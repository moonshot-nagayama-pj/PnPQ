from typing import Callable, Generator
from unittest.mock import Mock, create_autospec

import pytest

from pnpq.apt.connection import AptConnection
from pnpq.apt.protocol import (
    Address,
    AptMessage,
    AptMessage_MGMSG_MOT_GET_JOGPARAMS,
    AptMessage_MGMSG_MOT_GET_STATUSUPDATE_20_BYTES,
    AptMessage_MGMSG_MOT_GET_STATUSUPDATE_34_BYTES,
    AptMessage_MGMSG_MOT_GET_VELPARAMS,
    AptMessage_MGMSG_MOT_MOVE_ABSOLUTE,
    AptMessage_MGMSG_MOT_MOVE_COMPLETED_20_BYTES,
    AptMessage_MGMSG_MOT_MOVE_JOG,
    AptMessage_MGMSG_MOT_REQ_JOGPARAMS,
    AptMessage_MGMSG_MOT_REQ_STATUSUPDATE,
    AptMessage_MGMSG_MOT_REQ_VELPARAMS,
    AptMessage_MGMSG_MOT_SET_JOGPARAMS,
    AptMessage_MGMSG_MOT_SET_VELPARAMS,
    ChanIdent,
    JogDirection,
    JogMode,
    Status,
    StopMode,
    UStatus,
)
from pnpq.devices.waveplate_thorlabs_k10cr1 import (
    WaveplateJogParams,
    WaveplateThorlabsK10CR1,
    WaveplateVelocityParams,
)
from pnpq.errors import InvalidStateException
from pnpq.units import pnpq_ureg

status_message = AptMessage_MGMSG_MOT_GET_STATUSUPDATE_20_BYTES(
    chan_ident=ChanIdent(1),
    destination=Address.HOST_CONTROLLER,
    source=Address.GENERIC_USB,
    enc_count=0,
    position=0,
    status=Status(INMOTIONCCW=True, INMOTIONCW=True, HOMED=True),
)
status_message_34 = AptMessage_MGMSG_MOT_GET_STATUSUPDATE_34_BYTES(
    chan_ident_1=ChanIdent(1),
    chan_ident_2=ChanIdent(2),
    destination=Address.HOST_CONTROLLER,
    source=Address.GENERIC_USB,
    enc_count=0,
    position=0,
    status=Status(INMOTIONCCW=True, INMOTIONCW=True, HOMED=True),
    reserved1=0,
    reserved2=0,
    reserved3=0,
)


@pytest.fixture(name="mock_connection", scope="function")
def mock_connection_fixture() -> Generator[Mock]:
    connection = create_autospec(AptConnection)
    connection.stop_event = Mock()
    connection.tx_ordered_sender_awaiting_reply = Mock()
    connection.tx_ordered_sender_awaiting_reply.is_set = Mock(return_value=True)
    assert isinstance(connection, Mock)
    yield connection

    # Shut down the polling thread
    def mock_send_message_unordered(message: AptMessage) -> None:
        raise InvalidStateException("Tried to use a closed AptConnection object.")

    connection.send_message_unordered.side_effect = mock_send_message_unordered


def test_move_absolute(mock_connection: Mock) -> None:

    def mock_send_message_expect_reply(
        sent_message: AptMessage,
        match_reply_callback: Callable[
            [
                AptMessage,
            ],
            bool,
        ],
    ) -> (
        AptMessage_MGMSG_MOT_GET_STATUSUPDATE_20_BYTES | None
    ):  # Only used to check for 20 byte status messages

        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_STATUSUPDATE):
            return status_message

        if isinstance(sent_message, AptMessage_MGMSG_MOT_MOVE_ABSOLUTE):

            # A hypothetical reply message from the devices
            reply_message = AptMessage_MGMSG_MOT_MOVE_COMPLETED_20_BYTES(
                chan_ident=sent_message.chan_ident,
                position=sent_message.absolute_distance,
                velocity=0,
                destination=Address.HOST_CONTROLLER,
                source=Address.GENERIC_USB,
                motor_current=0 * pnpq_ureg.milliamp,
                status=UStatus(INMOTIONCCW=True, INMOTIONCW=True, ENABLED=True),
            )

            assert match_reply_callback(reply_message)
        return None

    mock_connection.send_message_expect_reply.side_effect = (
        mock_send_message_expect_reply
    )

    controller = WaveplateThorlabsK10CR1(connection=mock_connection)

    controller.move_absolute(10 * pnpq_ureg.k10cr1_step)

    # First call is to initialize and home.
    # Second call is for AptMessage_MGMSG_MOT_MOVE_ABSOLUTE.
    # (Enabling and disabling the channel doesn't use an expect reply in K10CR1)
    assert mock_connection.send_message_expect_reply.call_count == 2

    # Assert the message that is sent when K10CR1 initializes and homes
    first_call_args = mock_connection.send_message_expect_reply.call_args_list[0]
    assert isinstance(first_call_args[0][0], AptMessage_MGMSG_MOT_REQ_STATUSUPDATE)
    assert first_call_args[0][0].chan_ident == ChanIdent(1)
    assert first_call_args[0][0].destination == Address.GENERIC_USB
    assert first_call_args[0][0].source == Address.HOST_CONTROLLER

    # Assert the message that is sent to move the waveplate
    second_call_args = mock_connection.send_message_expect_reply.call_args_list[1]
    assert isinstance(second_call_args[0][0], AptMessage_MGMSG_MOT_MOVE_ABSOLUTE)
    assert second_call_args[0][0].absolute_distance == 10
    assert second_call_args[0][0].chan_ident == ChanIdent(1)
    assert second_call_args[0][0].destination == Address.GENERIC_USB
    assert second_call_args[0][0].source == Address.HOST_CONTROLLER


def test_jog(mock_connection: Mock) -> None:
    def mock_send_message_expect_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> AptMessage | None:
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_STATUSUPDATE):
            return status_message

        if isinstance(sent_message, AptMessage_MGMSG_MOT_MOVE_JOG):

            # A hypothetical reply message from the device
            reply_message = AptMessage_MGMSG_MOT_MOVE_COMPLETED_20_BYTES(
                chan_ident=sent_message.chan_ident,
                position=0,  # Inaccurate position, but it should be okay for this test.
                velocity=0,
                destination=Address.HOST_CONTROLLER,
                source=Address.GENERIC_USB,
                motor_current=0 * pnpq_ureg.milliamp,
                status=UStatus(INMOTIONCCW=True, INMOTIONCW=True, ENABLED=True),
            )

            assert match_reply_callback(reply_message)
        return None

    mock_connection.send_message_expect_reply.side_effect = (
        mock_send_message_expect_reply
    )

    controller = WaveplateThorlabsK10CR1(connection=mock_connection)

    controller.jog(jog_direction=JogDirection.FORWARD)

    # First call is to initialize and home.
    # Second call is for sending AptMessage_MGMSG_MOT_MOVE_JOG.
    # (Enabling and disabling the channel doesn't use an expect reply in K10CR1)
    assert mock_connection.send_message_expect_reply.call_count == 2

    first_call_args = mock_connection.send_message_expect_reply.call_args_list[0]
    assert isinstance(first_call_args[0][0], AptMessage_MGMSG_MOT_REQ_STATUSUPDATE)
    assert first_call_args[0][0].chan_ident == ChanIdent(1)
    assert first_call_args[0][0].destination == Address.GENERIC_USB
    assert first_call_args[0][0].source == Address.HOST_CONTROLLER

    # Assert the message that is sent to move the waveplate
    second_call_args = mock_connection.send_message_expect_reply.call_args_list[1]
    assert isinstance(second_call_args[0][0], AptMessage_MGMSG_MOT_MOVE_JOG)
    assert second_call_args[0][0].jog_direction == JogDirection.FORWARD
    assert second_call_args[0][0].chan_ident == ChanIdent(1)
    assert second_call_args[0][0].destination == Address.GENERIC_USB
    assert second_call_args[0][0].source == Address.HOST_CONTROLLER


def test_set_velparams(mock_connection: Mock) -> None:
    def mock_send_message_expect_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> AptMessage:
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_STATUSUPDATE):
            return status_message

        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_VELPARAMS):

            # A hypothetical reply message from the device
            reply_message = AptMessage_MGMSG_MOT_GET_VELPARAMS(
                destination=Address.HOST_CONTROLLER,
                source=Address.GENERIC_USB,
                chan_ident=ChanIdent(1),
                minimum_velocity=10,
                acceleration=20,
                maximum_velocity=30,
            )

            assert match_reply_callback(reply_message)
            return reply_message
        raise ValueError(f"Unexpected message type sent: {type(sent_message)}")

    mock_connection.send_message_expect_reply.side_effect = (
        mock_send_message_expect_reply
    )

    controller = WaveplateThorlabsK10CR1(connection=mock_connection)

    controller.set_velparams(
        minimum_velocity=1 * pnpq_ureg.k10cr1_velocity,
        acceleration=2 * pnpq_ureg.k10cr1_acceleration,
        maximum_velocity=3 * pnpq_ureg.k10cr1_velocity,
    )

    # First call is to initialize and home.
    # Second call is for AptMessage_MGMSG_MOT_REQ_VELPARAMS.
    # (Enabling and disabling the channel doesn't use an expect reply in K10CR1)
    assert mock_connection.send_message_expect_reply.call_count == 2

    # Assert the message that is sent when K10CR1 initializes and homes
    first_call_args = mock_connection.send_message_expect_reply.call_args_list[0]
    assert isinstance(first_call_args[0][0], AptMessage_MGMSG_MOT_REQ_STATUSUPDATE)
    assert first_call_args[0][0].chan_ident == ChanIdent(1)
    assert first_call_args[0][0].destination == Address.GENERIC_USB
    assert first_call_args[0][0].source == Address.HOST_CONTROLLER

    # First call is for AptMessage_MGMSG_HW_START_UPDATEMSGS.
    # Second call is for AptMessage_MGMSG_MOT_SET_VELPARAMS.
    # There may be subsequent calls.
    assert mock_connection.send_message_no_reply.call_count >= 2

    # Assert the message that is sent to move the waveplate
    second_call_args = mock_connection.send_message_no_reply.call_args_list[1]
    assert isinstance(second_call_args[0][0], AptMessage_MGMSG_MOT_SET_VELPARAMS)
    assert second_call_args[0][0].minimum_velocity == 1
    assert second_call_args[0][0].acceleration == 2
    assert second_call_args[0][0].maximum_velocity == 3
    assert second_call_args[0][0].chan_ident == ChanIdent(1)
    assert second_call_args[0][0].destination == Address.GENERIC_USB
    assert second_call_args[0][0].source == Address.HOST_CONTROLLER


def test_get_velparams(mock_connection: Mock) -> None:
    def mock_send_message_expect_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> AptMessage:
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_STATUSUPDATE):
            return status_message

        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_VELPARAMS):

            # A hypothetical reply message from the device
            reply_message = AptMessage_MGMSG_MOT_GET_VELPARAMS(
                destination=Address.HOST_CONTROLLER,
                source=Address.GENERIC_USB,
                chan_ident=ChanIdent(1),
                minimum_velocity=10,
                acceleration=20,
                maximum_velocity=30,
            )

            assert match_reply_callback(reply_message)
            return reply_message

        raise ValueError(f"Unexpected message type sent: {type(sent_message)}")

    mock_connection.send_message_expect_reply.side_effect = (
        mock_send_message_expect_reply
    )

    controller = WaveplateThorlabsK10CR1(connection=mock_connection)

    params: WaveplateVelocityParams = controller.get_velparams()

    assert params == {
        "minimum_velocity": 10 * pnpq_ureg.k10cr1_velocity,
        "acceleration": 20 * pnpq_ureg.k10cr1_acceleration,
        "maximum_velocity": 30 * pnpq_ureg.k10cr1_velocity,
    }

    # First call is to initialize and home.
    # Second call is for AptMessage_MGMSG_MOT_REQ_VELPARAMS.
    # (Enabling and disabling the channel doesn't use an expect reply in K10CR1)
    assert mock_connection.send_message_expect_reply.call_count == 2

    # Assert the message that is sent when K10CR1 initializes and homes
    first_call_args = mock_connection.send_message_expect_reply.call_args_list[0]
    assert isinstance(first_call_args[0][0], AptMessage_MGMSG_MOT_REQ_STATUSUPDATE)
    assert first_call_args[0][0].chan_ident == ChanIdent(1)
    assert first_call_args[0][0].destination == Address.GENERIC_USB
    assert first_call_args[0][0].source == Address.HOST_CONTROLLER

    # Assert the message that is sent to move the waveplate
    second_call_args = mock_connection.send_message_expect_reply.call_args_list[1]
    assert isinstance(second_call_args[0][0], AptMessage_MGMSG_MOT_REQ_VELPARAMS)
    assert second_call_args[0][0].chan_ident == ChanIdent(1)
    assert second_call_args[0][0].destination == Address.GENERIC_USB
    assert second_call_args[0][0].source == Address.HOST_CONTROLLER


def test_set_jogparams(mock_connection: Mock) -> None:
    def mock_send_message_expect_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> AptMessage:
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_STATUSUPDATE):
            return status_message

        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_JOGPARAMS):

            # A hypothetical reply message from the device
            reply_message = AptMessage_MGMSG_MOT_GET_JOGPARAMS(
                destination=Address.HOST_CONTROLLER,
                source=Address.GENERIC_USB,
                chan_ident=ChanIdent(1),
                jog_mode=JogMode.CONTINUOUS,
                jog_step_size=10,
                jog_minimum_velocity=20,
                jog_acceleration=30,
                jog_maximum_velocity=40,
                jog_stop_mode=StopMode.CONTROLLED,
            )

            assert match_reply_callback(reply_message)
            return reply_message
        raise ValueError(f"Unexpected message type sent: {type(sent_message)}")

    mock_connection.send_message_expect_reply.side_effect = (
        mock_send_message_expect_reply
    )

    controller = WaveplateThorlabsK10CR1(connection=mock_connection)

    controller.set_jogparams(
        jog_mode=JogMode.SINGLE_STEP,
        jog_step_size=1 * pnpq_ureg("k10cr1_step"),
        jog_minimum_velocity=2 * pnpq_ureg("k10cr1_velocity"),
        jog_acceleration=3 * pnpq_ureg("k10cr1_acceleration"),
        jog_maximum_velocity=4 * pnpq_ureg("k10cr1_velocity"),
        jog_stop_mode=StopMode.IMMEDIATE,
    )

    # First call is to initialize and home.
    # Second call is for AptMessage_MGMSG_MOT_REQ_JOGPARAMS.
    # (Enabling and disabling the channel doesn't use an expect reply in K10CR1)
    assert mock_connection.send_message_expect_reply.call_count == 2

    # Assert the message that is sent when K10CR1 initializes and homes
    first_call_args = mock_connection.send_message_expect_reply.call_args_list[0]
    assert isinstance(first_call_args[0][0], AptMessage_MGMSG_MOT_REQ_STATUSUPDATE)
    assert first_call_args[0][0].chan_ident == ChanIdent(1)
    assert first_call_args[0][0].destination == Address.GENERIC_USB
    assert first_call_args[0][0].source == Address.HOST_CONTROLLER

    # First call is for AptMessage_MGMSG_HW_START_UPDATEMSGS.
    # Second call is for AptMessage_MGMSG_MOT_SET_JOGPARAMS.
    # There may be subsequent calls.
    assert mock_connection.send_message_no_reply.call_count >= 2

    # Assert the message that is sent to move the waveplate
    second_call_args = mock_connection.send_message_no_reply.call_args_list[1]
    assert isinstance(second_call_args[0][0], AptMessage_MGMSG_MOT_SET_JOGPARAMS)
    assert second_call_args[0][0].jog_mode == JogMode.SINGLE_STEP
    assert second_call_args[0][0].jog_step_size == 1
    assert second_call_args[0][0].jog_minimum_velocity == 2
    assert second_call_args[0][0].jog_acceleration == 3
    assert second_call_args[0][0].jog_maximum_velocity == 4
    assert second_call_args[0][0].chan_ident == ChanIdent(1)
    assert second_call_args[0][0].destination == Address.GENERIC_USB
    assert second_call_args[0][0].source == Address.HOST_CONTROLLER


def test_get_jogparams(mock_connection: Mock) -> None:
    def mock_send_message_expect_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> AptMessage:
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_STATUSUPDATE):
            return status_message

        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_JOGPARAMS):

            # A hypothetical reply message from the device
            reply_message = AptMessage_MGMSG_MOT_GET_JOGPARAMS(
                destination=Address.HOST_CONTROLLER,
                source=Address.GENERIC_USB,
                chan_ident=ChanIdent(1),
                jog_mode=JogMode.CONTINUOUS,
                jog_step_size=10,
                jog_minimum_velocity=20,
                jog_acceleration=30,
                jog_maximum_velocity=40,
                jog_stop_mode=StopMode.CONTROLLED,
            )

            assert match_reply_callback(reply_message)
            return reply_message

        raise ValueError(f"Unexpected message type sent: {type(sent_message)}")

    mock_connection.send_message_expect_reply.side_effect = (
        mock_send_message_expect_reply
    )

    controller = WaveplateThorlabsK10CR1(connection=mock_connection)

    params: WaveplateJogParams = controller.get_jogparams()

    assert params == {
        "jog_mode": JogMode.CONTINUOUS,
        "jog_step_size": 10 * pnpq_ureg.k10cr1_step,
        "jog_minimum_velocity": 20 * pnpq_ureg.k10cr1_velocity,
        "jog_acceleration": 30 * pnpq_ureg.k10cr1_acceleration,
        "jog_maximum_velocity": 40 * pnpq_ureg.k10cr1_velocity,
        "jog_stop_mode": StopMode.CONTROLLED,
    }

    # First call is to initialize and home.
    # Second call is for AptMessage_MGMSG_MOT_REQ_JOGPARAMS.
    # (Enabling and disabling the channel doesn't use an expect reply in K10CR1)
    assert mock_connection.send_message_expect_reply.call_count == 2

    # Assert the message that is sent when K10CR1 initializes and homes
    first_call_args = mock_connection.send_message_expect_reply.call_args_list[0]
    assert isinstance(first_call_args[0][0], AptMessage_MGMSG_MOT_REQ_STATUSUPDATE)
    assert first_call_args[0][0].chan_ident == ChanIdent(1)
    assert first_call_args[0][0].destination == Address.GENERIC_USB
    assert first_call_args[0][0].source == Address.HOST_CONTROLLER

    # Assert the message that is sent to move the waveplate
    second_call_args = mock_connection.send_message_expect_reply.call_args_list[1]
    assert isinstance(second_call_args[0][0], AptMessage_MGMSG_MOT_REQ_JOGPARAMS)
    assert second_call_args[0][0].chan_ident == ChanIdent(1)
    assert second_call_args[0][0].destination == Address.GENERIC_USB
    assert second_call_args[0][0].source == Address.HOST_CONTROLLER
