from typing import Callable, Generator
from unittest.mock import Mock, create_autospec

import pytest

from pnpq.apt.connection import AptConnection
from pnpq.apt.protocol import (
    Address,
    AptMessage,
    AptMessage_MGMSG_MOD_IDENTIFY,
    AptMessage_MGMSG_MOT_GET_HOMEPARAMS,
    AptMessage_MGMSG_MOT_GET_JOGPARAMS,
    AptMessage_MGMSG_MOT_GET_USTATUSUPDATE,
    AptMessage_MGMSG_MOT_GET_VELPARAMS,
    AptMessage_MGMSG_MOT_MOVE_ABSOLUTE,
    AptMessage_MGMSG_MOT_MOVE_COMPLETED_20_BYTES,
    AptMessage_MGMSG_MOT_MOVE_HOME,
    AptMessage_MGMSG_MOT_MOVE_HOMED,
    AptMessage_MGMSG_MOT_MOVE_JOG,
    AptMessage_MGMSG_MOT_REQ_HOMEPARAMS,
    AptMessage_MGMSG_MOT_REQ_JOGPARAMS,
    AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE,
    AptMessage_MGMSG_MOT_REQ_VELPARAMS,
    AptMessage_MGMSG_MOT_SET_HOMEPARAMS,
    AptMessage_MGMSG_MOT_SET_JOGPARAMS,
    AptMessage_MGMSG_MOT_SET_VELPARAMS,
    ChanIdent,
    HomeDirection,
    JogDirection,
    JogMode,
    LimitSwitch,
    StopMode,
    UStatus,
)
from pnpq.devices.odl_thorlabs_kbd101 import (
    OpticalDelayLineThorlabsKBD101,
)
from pnpq.errors import InvalidStateException
from pnpq.units import pnpq_ureg


@pytest.fixture(name="mock_connection", scope="function")
def mock_connection_fixture() -> Generator[Mock, None, None]:
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


ustatus_message = AptMessage_MGMSG_MOT_GET_USTATUSUPDATE(
    chan_ident=ChanIdent(1),
    destination=Address.HOST_CONTROLLER,
    source=Address.GENERIC_USB,
    velocity=0,
    position=0,
    motor_current=0 * pnpq_ureg.milliamp,
    status=UStatus(INMOTIONCCW=False, INMOTIONCW=False, HOMED=True),
)


def test_identify(mock_connection: Mock) -> None:
    def send_no_reply(sent_message: AptMessage) -> None:
        if isinstance(sent_message, AptMessage_MGMSG_MOD_IDENTIFY):
            assert sent_message.chan_ident == ChanIdent(1)
            assert sent_message.destination == Address.GENERIC_USB
            assert sent_message.source == Address.HOST_CONTROLLER

    mock_connection.send_message_no_reply.side_effect = send_no_reply

    odl = OpticalDelayLineThorlabsKBD101(connection=mock_connection)
    odl.identify()

    # One call to send MGMSG_HW_START_UPDATEMSGS, and the other for MGMSG_MOD_IDENTIFY
    assert mock_connection.send_message_no_reply.call_count == 2

    # Assert function called with correct parameters
    first_call_args = mock_connection.send_message_no_reply.call_args_list[1]
    assert isinstance(first_call_args[0][0], AptMessage_MGMSG_MOD_IDENTIFY)
    assert first_call_args[0][0].chan_ident == ChanIdent(1)
    assert first_call_args[0][0].destination == Address.GENERIC_USB
    assert first_call_args[0][0].source == Address.HOST_CONTROLLER


def test_home(mock_connection: Mock) -> None:

    def mock_send_message_expect_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> AptMessage:
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE):
            return ustatus_message
        if isinstance(sent_message, AptMessage_MGMSG_MOT_MOVE_HOME):
            reply = AptMessage_MGMSG_MOT_MOVE_HOMED(
                chan_ident=sent_message.chan_ident,
                destination=Address.HOST_CONTROLLER,
                source=Address.GENERIC_USB,
            )
            assert match_reply_callback(reply)
            return reply
        raise ValueError(f"Unexpected message type: {type(sent_message)}. ")

    mock_connection.send_message_expect_reply.side_effect = (
        mock_send_message_expect_reply
    )

    odl = OpticalDelayLineThorlabsKBD101(connection=mock_connection)
    odl.home()

    # First call is to initialize and home.
    # Second call is for AptMessage_MGMSG_MOT_MOVE_HOME.
    # (Enabling and disabling the channel doesn't use an expect reply in KBD101)
    assert mock_connection.send_message_expect_reply.call_count == 2

    # Assert the message that is sent when KBD101 initializes and homes
    first_call_args = mock_connection.send_message_expect_reply.call_args_list[0]
    assert isinstance(first_call_args[0][0], AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE)
    assert first_call_args[0][0].chan_ident == ChanIdent(1)
    assert first_call_args[0][0].destination == Address.GENERIC_USB
    assert first_call_args[0][0].source == Address.HOST_CONTROLLER

    # Assert the message that is sent to move the ODL
    second_call_args = mock_connection.send_message_expect_reply.call_args_list[1]
    assert isinstance(second_call_args[0][0], AptMessage_MGMSG_MOT_MOVE_HOME)
    assert second_call_args[0][0].chan_ident == ChanIdent(1)
    assert second_call_args[0][0].destination == Address.GENERIC_USB
    assert second_call_args[0][0].source == Address.HOST_CONTROLLER


def test_move_absolute(mock_connection: Mock) -> None:

    def mock_send_message_expect_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> AptMessage:
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE):
            return ustatus_message

        if isinstance(sent_message, AptMessage_MGMSG_MOT_MOVE_ABSOLUTE):
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
            return reply_message
        raise ValueError(f"Unexpected message type: {type(sent_message)}. ")

    mock_connection.send_message_expect_reply.side_effect = (
        mock_send_message_expect_reply
    )

    controller = OpticalDelayLineThorlabsKBD101(connection=mock_connection)
    controller.move_absolute(1000 * pnpq_ureg.kbd101_position)

    # First call is to initialize and home.
    # Second call is for AptMessage_MGMSG_MOT_MOVE_ABSOLUTE.
    # (Enabling and disabling the channel doesn't use an expect reply in KBD101)
    assert mock_connection.send_message_expect_reply.call_count == 2

    # Assert the message that is sent when KBD101 initializes and homes
    first_call_args = mock_connection.send_message_expect_reply.call_args_list[0]
    assert isinstance(first_call_args[0][0], AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE)
    assert first_call_args[0][0].chan_ident == ChanIdent(1)
    assert first_call_args[0][0].destination == Address.GENERIC_USB
    assert first_call_args[0][0].source == Address.HOST_CONTROLLER

    # Assert the message that is sent to move the ODL
    second_call_args = mock_connection.send_message_expect_reply.call_args_list[1]
    assert isinstance(second_call_args[0][0], AptMessage_MGMSG_MOT_MOVE_ABSOLUTE)
    assert second_call_args[0][0].chan_ident == ChanIdent(1)
    assert second_call_args[0][0].destination == Address.GENERIC_USB
    assert second_call_args[0][0].source == Address.HOST_CONTROLLER
    assert second_call_args[0][0].absolute_distance == 1000


def test_jog(mock_connection: Mock) -> None:
    def mock_send_message_expect_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> AptMessage:
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE):
            return ustatus_message

        if isinstance(sent_message, AptMessage_MGMSG_MOT_MOVE_JOG):
            reply = AptMessage_MGMSG_MOT_MOVE_COMPLETED_20_BYTES(
                chan_ident=sent_message.chan_ident,
                position=0,
                velocity=0,
                destination=Address.HOST_CONTROLLER,
                source=Address.GENERIC_USB,
                motor_current=0 * pnpq_ureg.milliamp,
                status=UStatus(INMOTIONCCW=False, INMOTIONCW=False, ENABLED=True),
            )
            assert match_reply_callback(reply)
            return reply
        raise ValueError(f"Unexpected message type: {type(sent_message)}. ")

    mock_connection.send_message_expect_reply.side_effect = (
        mock_send_message_expect_reply
    )

    odl = OpticalDelayLineThorlabsKBD101(connection=mock_connection)
    odl.jog(JogDirection.FORWARD)

    # First call is to initialize and home.
    # Second call is for AptMessage_MGMSG_MOT_MOVE_JOG.
    # (Enabling and disabling the channel doesn't use an expect reply in KBD101)
    assert mock_connection.send_message_expect_reply.call_count == 2

    # Assert the message that is sent when KBD101 initializes and homes
    first_call_args = mock_connection.send_message_expect_reply.call_args_list[0]
    assert isinstance(first_call_args[0][0], AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE)
    assert first_call_args[0][0].chan_ident == ChanIdent(1)
    assert first_call_args[0][0].destination == Address.GENERIC_USB
    assert first_call_args[0][0].source == Address.HOST_CONTROLLER

    # Assert the message that is sent to move the ODL
    second_call_args = mock_connection.send_message_expect_reply.call_args_list[1]
    assert isinstance(second_call_args[0][0], AptMessage_MGMSG_MOT_MOVE_JOG)
    assert second_call_args[0][0].chan_ident == ChanIdent(1)
    assert second_call_args[0][0].destination == Address.GENERIC_USB
    assert second_call_args[0][0].source == Address.HOST_CONTROLLER
    assert second_call_args[0][0].jog_direction == JogDirection.FORWARD


def test_get_velparams(mock_connection: Mock) -> None:
    def mock_send_message_expect_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> AptMessage:
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE):
            return ustatus_message
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_VELPARAMS):
            reply = AptMessage_MGMSG_MOT_GET_VELPARAMS(
                chan_ident=sent_message.chan_ident,
                destination=Address.HOST_CONTROLLER,
                source=Address.GENERIC_USB,
                minimum_velocity=1,
                acceleration=2,
                maximum_velocity=3,
            )
            assert match_reply_callback(reply)
            return reply
        raise ValueError(f"Unexpected message type: {type(sent_message)}. ")

    mock_connection.send_message_expect_reply.side_effect = (
        mock_send_message_expect_reply
    )

    odl = OpticalDelayLineThorlabsKBD101(connection=mock_connection)
    velparams = odl.get_velparams()

    assert velparams == {
        "minimum_velocity": 1 * pnpq_ureg.kbd101_velocity,
        "acceleration": 2 * pnpq_ureg.kbd101_acceleration,
        "maximum_velocity": 3 * pnpq_ureg.kbd101_velocity,
    }

    # First call is to initialize and home.
    # Second call is for AptMessage_MGMSG_MOT_REQ_VELPARAMS.
    # (Enabling and disabling the channel doesn't use an expect reply in KBD101)
    assert mock_connection.send_message_expect_reply.call_count == 2

    # Assert the message that is sent when KBD101 initializes and homes
    first_call_args = mock_connection.send_message_expect_reply.call_args_list[0]
    assert isinstance(first_call_args[0][0], AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE)
    assert first_call_args[0][0].chan_ident == ChanIdent(1)
    assert first_call_args[0][0].destination == Address.GENERIC_USB
    assert first_call_args[0][0].source == Address.HOST_CONTROLLER

    # Assert the message that is sent to move the ODL
    second_call_args = mock_connection.send_message_expect_reply.call_args_list[1]
    assert isinstance(second_call_args[0][0], AptMessage_MGMSG_MOT_REQ_VELPARAMS)
    assert second_call_args[0][0].chan_ident == ChanIdent(1)
    assert second_call_args[0][0].destination == Address.GENERIC_USB
    assert second_call_args[0][0].source == Address.HOST_CONTROLLER


def test_set_velparams(mock_connection: Mock) -> None:
    def mock_send_message_expect_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> AptMessage:
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE):
            return ustatus_message

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

    controller = OpticalDelayLineThorlabsKBD101(connection=mock_connection)

    controller.set_velparams(
        minimum_velocity=1 * pnpq_ureg.kbd101_velocity,
        acceleration=2 * pnpq_ureg.kbd101_acceleration,
        maximum_velocity=3 * pnpq_ureg.kbd101_velocity,
    )

    # First call is to initialize and home.
    # Second call is for AptMessage_MGMSG_MOT_REQ_VELPARAMS.
    # (Enabling and disabling the channel doesn't use an expect reply in KBD101)
    assert mock_connection.send_message_expect_reply.call_count == 2

    # Assert the message that is sent when KBD101 initializes and homes
    first_call_args = mock_connection.send_message_expect_reply.call_args_list[0]
    assert isinstance(first_call_args[0][0], AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE)
    assert first_call_args[0][0].chan_ident == ChanIdent(1)
    assert first_call_args[0][0].destination == Address.GENERIC_USB
    assert first_call_args[0][0].source == Address.HOST_CONTROLLER

    # First call is for AptMessage_MGMSG_HW_START_UPDATEMSGS.
    # Second call is for AptMessage_MGMSG_MOT_SET_VELPARAMS.
    # There may be subsequent calls.
    assert mock_connection.send_message_no_reply.call_count >= 2

    # Assert the message that is sent to move the ODL
    second_call_args = mock_connection.send_message_no_reply.call_args_list[1]
    assert isinstance(second_call_args[0][0], AptMessage_MGMSG_MOT_SET_VELPARAMS)
    assert second_call_args[0][0].minimum_velocity == 1
    assert second_call_args[0][0].acceleration == 2
    assert second_call_args[0][0].maximum_velocity == 3
    assert second_call_args[0][0].chan_ident == ChanIdent(1)
    assert second_call_args[0][0].destination == Address.GENERIC_USB
    assert second_call_args[0][0].source == Address.HOST_CONTROLLER


def test_get_homeparams(mock_connection: Mock) -> None:
    def mock_send_message_expect_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> AptMessage:
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE):
            return ustatus_message

        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_HOMEPARAMS):

            # A hypothetical reply message from the device
            reply_message = AptMessage_MGMSG_MOT_GET_HOMEPARAMS(
                destination=Address.HOST_CONTROLLER,
                source=Address.GENERIC_USB,
                chan_ident=ChanIdent(1),
                home_direction=HomeDirection.FORWARD,
                limit_switch=LimitSwitch.HARDWARE_FORWARD,
                home_velocity=1 * pnpq_ureg.kbd101_velocity,
                offset_distance=2 * pnpq_ureg.kbd101_position,
            )

            assert match_reply_callback(reply_message)
            return reply_message
        raise ValueError(f"Unexpected message type sent: {type(sent_message)}")

    mock_connection.send_message_expect_reply.side_effect = (
        mock_send_message_expect_reply
    )

    controller = OpticalDelayLineThorlabsKBD101(connection=mock_connection)

    params = controller.get_homeparams()
    assert params == {
        "home_direction": HomeDirection.FORWARD,
        "limit_switch": LimitSwitch.HARDWARE_FORWARD,
        "home_velocity": 1 * pnpq_ureg.kbd101_velocity,
        "offset_distance": 2 * pnpq_ureg.kbd101_position,
    }

    # First call is to initialize and home.
    # Second call is for AptMessage_MGMSG_MOT_REQ_HOMEPARAMS.
    # (Enabling and disabling the channel doesn't use an expect reply in KBD101)
    assert mock_connection.send_message_expect_reply.call_count == 2

    # Assert the message that is sent when KBD101 initializes and homes
    first_call_args = mock_connection.send_message_expect_reply.call_args_list[0]
    assert isinstance(first_call_args[0][0], AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE)
    assert first_call_args[0][0].chan_ident == ChanIdent(1)
    assert first_call_args[0][0].destination == Address.GENERIC_USB
    assert first_call_args[0][0].source == Address.HOST_CONTROLLER

    # Assert the message that is sent to move the ODL
    second_call_args = mock_connection.send_message_expect_reply.call_args_list[1]
    assert isinstance(second_call_args[0][0], AptMessage_MGMSG_MOT_REQ_HOMEPARAMS)
    assert second_call_args[0][0].chan_ident == ChanIdent(1)
    assert second_call_args[0][0].destination == Address.GENERIC_USB
    assert second_call_args[0][0].source == Address.HOST_CONTROLLER


def test_set_homeparams(mock_connection: Mock) -> None:
    def mock_send_message_expect_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> AptMessage:
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE):
            return ustatus_message

        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_HOMEPARAMS):

            # A hypothetical reply message from the device
            reply_message = AptMessage_MGMSG_MOT_GET_HOMEPARAMS(
                destination=Address.HOST_CONTROLLER,
                source=Address.GENERIC_USB,
                chan_ident=ChanIdent(1),
                home_direction=HomeDirection.FORWARD,
                limit_switch=LimitSwitch.HARDWARE_FORWARD,
                home_velocity=10 * pnpq_ureg.kbd101_velocity,
                offset_distance=20 * pnpq_ureg.kbd101_position,
            )

            assert match_reply_callback(reply_message)
            return reply_message
        raise ValueError(f"Unexpected message type sent: {type(sent_message)}")

    mock_connection.send_message_expect_reply.side_effect = (
        mock_send_message_expect_reply
    )

    controller = OpticalDelayLineThorlabsKBD101(connection=mock_connection)

    controller.set_homeparams(
        home_direction=HomeDirection.FORWARD,
        limit_switch=LimitSwitch.HARDWARE_FORWARD,
        home_velocity=1 * pnpq_ureg.kbd101_velocity,
        offset_distance=2 * pnpq_ureg.kbd101_position,
    )

    # First call is to initialize and home.
    # Second call is for AptMessage_MGMSG_MOT_REQ_HOMEPARAMS.
    # (Enabling and disabling the channel doesn't use an expect reply in KBD101)
    assert mock_connection.send_message_expect_reply.call_count == 2

    # Assert the message that is sent when KBD101 initializes and homes
    first_call_args = mock_connection.send_message_expect_reply.call_args_list[0]
    assert isinstance(first_call_args[0][0], AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE)
    assert first_call_args[0][0].chan_ident == ChanIdent(1)
    assert first_call_args[0][0].destination == Address.GENERIC_USB
    assert first_call_args[0][0].source == Address.HOST_CONTROLLER

    # First call is for AptMessage_MGMSG_HW_START_UPDATEMSGS.
    # Second call is for AptMessage_MGMSG_MOT_SET_HOMEPARAMS.
    # There may be subsequent calls.
    assert mock_connection.send_message_no_reply.call_count >= 2

    # Assert the message that is sent to move the ODL
    second_call_args = mock_connection.send_message_no_reply.call_args_list[1]
    assert isinstance(second_call_args[0][0], AptMessage_MGMSG_MOT_SET_HOMEPARAMS)
    assert second_call_args[0][0].home_direction == HomeDirection.FORWARD
    assert second_call_args[0][0].limit_switch == LimitSwitch.HARDWARE_FORWARD
    assert second_call_args[0][0].home_velocity == 1
    assert second_call_args[0][0].offset_distance == 2
    assert second_call_args[0][0].chan_ident == ChanIdent(1)
    assert second_call_args[0][0].destination == Address.GENERIC_USB
    assert second_call_args[0][0].source == Address.HOST_CONTROLLER


def test_set_jogparams(mock_connection: Mock) -> None:
    def mock_send_message_expect_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> AptMessage:
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE):
            return ustatus_message

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

    controller = OpticalDelayLineThorlabsKBD101(connection=mock_connection)

    controller.set_jogparams(
        jog_mode=JogMode.CONTINUOUS,
        jog_step_size=1 * pnpq_ureg.kbd101_position,
        jog_minimum_velocity=2 * pnpq_ureg.kbd101_velocity,
        jog_acceleration=3 * pnpq_ureg.kbd101_acceleration,
        jog_maximum_velocity=4 * pnpq_ureg.kbd101_velocity,
        jog_stop_mode=StopMode.CONTROLLED,
    )

    # First call is to initialize and home.
    # Second call is for AptMessage_MGMSG_MOT_REQ_JOGPARAMS.
    # (Enabling and disabling the channel doesn't use an expect reply in KBD101)
    assert mock_connection.send_message_expect_reply.call_count == 2

    # Assert the message that is sent when KBD101 initializes and homes
    first_call_args = mock_connection.send_message_expect_reply.call_args_list[0]
    assert isinstance(first_call_args[0][0], AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE)
    assert first_call_args[0][0].chan_ident == ChanIdent(1)
    assert first_call_args[0][0].destination == Address.GENERIC_USB
    assert first_call_args[0][0].source == Address.HOST_CONTROLLER

    # First call is for AptMessage_MGMSG_HW_START_UPDATEMSGS.
    # Second call is for AptMessage_MGMSG_MOT_SET_JOGPARAMS.
    # There may be subsequent calls.
    assert mock_connection.send_message_no_reply.call_count >= 2

    # Assert the message that is sent to move the ODL
    second_call_args = mock_connection.send_message_no_reply.call_args_list[1]
    assert isinstance(second_call_args[0][0], AptMessage_MGMSG_MOT_SET_JOGPARAMS)
    assert second_call_args[0][0].jog_mode == JogMode.CONTINUOUS
    assert second_call_args[0][0].jog_step_size == 1
    assert second_call_args[0][0].jog_minimum_velocity == 2
    assert second_call_args[0][0].jog_acceleration == 3
    assert second_call_args[0][0].jog_maximum_velocity == 4
    assert second_call_args[0][0].jog_stop_mode == StopMode.CONTROLLED
    assert second_call_args[0][0].chan_ident == ChanIdent(1)
    assert second_call_args[0][0].destination == Address.GENERIC_USB
    assert second_call_args[0][0].source == Address.HOST_CONTROLLER


def test_get_jogparams(mock_connection: Mock) -> None:
    def mock_send_message_expect_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> AptMessage:
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE):
            return ustatus_message

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

    controller = OpticalDelayLineThorlabsKBD101(connection=mock_connection)

    params = controller.get_jogparams()
    assert params == {
        "jog_mode": JogMode.CONTINUOUS,
        "jog_step_size": 10 * pnpq_ureg.kbd101_position,
        "jog_minimum_velocity": 20 * pnpq_ureg.kbd101_velocity,
        "jog_acceleration": 30 * pnpq_ureg.kbd101_acceleration,
        "jog_maximum_velocity": 40 * pnpq_ureg.kbd101_velocity,
        "jog_stop_mode": StopMode.CONTROLLED,
    }

    # First call is to initialize and home.
    # Second call is for AptMessage_MGMSG_MOT_REQ_JOGPARAMS.
    # (Enabling and disabling the channel doesn't use an expect reply in KBD101)
    assert mock_connection.send_message_expect_reply.call_count == 2

    # Assert the message that is sent when KBD101 initializes and homes
    first_call_args = mock_connection.send_message_expect_reply.call_args_list[0]
    assert isinstance(first_call_args[0][0], AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE)
    assert first_call_args[0][0].chan_ident == ChanIdent(1)
    assert first_call_args[0][0].destination == Address.GENERIC_USB
    assert first_call_args[0][0].source == Address.HOST_CONTROLLER

    # Assert the message that is sent to move the ODL
    second_call_args = mock_connection.send_message_expect_reply.call_args_list[1]
    assert isinstance(second_call_args[0][0], AptMessage_MGMSG_MOT_REQ_JOGPARAMS)
    assert second_call_args[0][0].chan_ident == ChanIdent(1)
    assert second_call_args[0][0].destination == Address.GENERIC_USB
    assert second_call_args[0][0].source == Address.HOST_CONTROLLER


def test_get_status(mock_connection: Mock) -> None:
    custom_ustatus_message = AptMessage_MGMSG_MOT_GET_USTATUSUPDATE(
        chan_ident=ChanIdent(1),
        destination=Address.HOST_CONTROLLER,
        source=Address.GENERIC_USB,
        velocity=1,
        position=2,
        motor_current=3 * pnpq_ureg.milliamp,
        status=UStatus(INMOTIONCCW=True, INMOTIONCW=True, HOMED=False),
    )

    mock_connection.send_message_expect_reply.side_effect = (
        ustatus_message,
        custom_ustatus_message,
    )

    controller = OpticalDelayLineThorlabsKBD101(connection=mock_connection)

    params: AptMessage_MGMSG_MOT_GET_USTATUSUPDATE = controller.get_status()
    assert params.chan_ident == ChanIdent(1)
    assert params.destination == Address.HOST_CONTROLLER
    assert params.source == Address.GENERIC_USB
    assert params.velocity == 1
    assert params.position == 2
    assert params.motor_current == 3 * pnpq_ureg.milliamp
    assert params.status == UStatus(INMOTIONCCW=True, INMOTIONCW=True, HOMED=False)

    # First call is to initialize and home.
    # Second call is for AptMessage_MGMSG_MOT_GET_USTATUSUPDATE.
    # (Enabling and disabling the channel doesn't use an expect reply in KBD101)
    assert mock_connection.send_message_expect_reply.call_count == 2

    # Assert the message that is sent when KBD101 initializes and homes
    first_call_args = mock_connection.send_message_expect_reply.call_args_list[0]
    assert isinstance(first_call_args[0][0], AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE)
    assert first_call_args[0][0].chan_ident == ChanIdent(1)
    assert first_call_args[0][0].destination == Address.GENERIC_USB
    assert first_call_args[0][0].source == Address.HOST_CONTROLLER
