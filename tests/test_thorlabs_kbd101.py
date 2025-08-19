from typing import Callable
from unittest.mock import Mock, create_autospec

import pytest

from pnpq.apt.connection import AptConnection
from pnpq.apt.protocol import (
    Address,
    AptMessage,
    AptMessage_MGMSG_MOT_GET_USTATUSUPDATE,
    AptMessage_MGMSG_MOT_MOVE_ABSOLUTE,
    AptMessage_MGMSG_MOT_MOVE_COMPLETED_20_BYTES,
    AptMessage_MGMSG_MOT_MOVE_HOMED,
    AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE,
    AptMessage_MGMSG_MOD_IDENTIFY,
    AptMessage_MGMSG_MOT_MOVE_HOME,
    AptMessage_MGMSG_MOT_MOVE_JOG,
    AptMessage_MGMSG_MOT_REQ_VELPARAMS,
    AptMessage_MGMSG_MOT_GET_VELPARAMS,
    AptMessage_MGMSG_MOT_SET_VELPARAMS,
    AptMessage_MGMSG_MOT_REQ_HOMEPARAMS,
    AptMessage_MGMSG_MOT_GET_HOMEPARAMS,
    AptMessage_MGMSG_MOT_SET_HOMEPARAMS,
    AptMessage_MGMSG_MOT_REQ_JOGPARAMS,
    AptMessage_MGMSG_MOT_GET_JOGPARAMS,
    AptMessage_MGMSG_MOT_SET_JOGPARAMS,
    ChanIdent,
    JogDirection,
    JogMode,
    HomeDirection,
    LimitSwitch,
    StopMode,
    UStatus,
)
from pnpq.devices.odl_thorlabs_kbd101 import (
    OpticalDelayLineThorlabsKBD101,
    OpticalDelayLineVelocityParams,
    OpticalDelayLineHomeParams,
    OpticalDelayLineJogParams,
)
from pnpq.units import pnpq_ureg


@pytest.fixture(name="mock_connection", scope="function")
def mock_connection_fixture() -> Mock:
    connection = create_autospec(AptConnection)
    connection.stop_event = Mock()
    connection.tx_ordered_sender_awaiting_reply = Mock()
    connection.tx_ordered_sender_awaiting_reply.is_set = Mock(return_value=True)
    assert isinstance(connection, Mock)
    return connection


def make_ustatus(homed: bool = True) -> AptMessage_MGMSG_MOT_GET_USTATUSUPDATE:
    return AptMessage_MGMSG_MOT_GET_USTATUSUPDATE(
        chan_ident=ChanIdent(1),
        destination=Address.HOST_CONTROLLER,
        source=Address.GENERIC_USB,
        velocity=0,
        position=0,
        motor_current=0 * pnpq_ureg.milliamp,
        status=UStatus(INMOTIONCCW=False, INMOTIONCW=False, HOMED=homed),
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
    ustatus = make_ustatus(homed=True)

    def expect_reply(sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]):
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE):
            return ustatus
        if isinstance(sent_message, AptMessage_MGMSG_MOT_MOVE_HOME):
            reply = AptMessage_MGMSG_MOT_MOVE_HOMED(
                chan_ident=sent_message.chan_ident,
                destination=Address.HOST_CONTROLLER,
                source=Address.GENERIC_USB,

            )
            assert match_reply_callback(reply)
            return reply
        return None

    mock_connection.send_message_expect_reply.side_effect = expect_reply

    odl = OpticalDelayLineThorlabsKBD101(connection=mock_connection)
    odl.home()

    # # First call is to initialize and home.
    # Second call is for AptMessage_MGMSG_MOT_MOVE_HOME.
    # (Enabling and disabling the channel doesn't use an expect reply in KBD101)
    assert mock_connection.send_message_expect_reply.call_count == 2



def test_move_absolute(mock_connection: Mock) -> None:
    ustatus_message = make_ustatus(homed=True)

    def mock_send_message_expect_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> AptMessage | None:
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE):
            return ustatus_message

        if isinstance(sent_message, AptMessage_MGMSG_MOT_MOVE_ABSOLUTE):
            # controller should convert the Quantity to a numeric payload
            assert sent_message.chan_ident == ChanIdent(1)
            # calling move_absolute(1000 * kbd101_position) -> payload 1000
            assert sent_message.absolute_distance == 1000

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
        return None

    mock_connection.send_message_expect_reply.side_effect = mock_send_message_expect_reply

    controller = OpticalDelayLineThorlabsKBD101(connection=mock_connection)
    controller.move_absolute(1000 * pnpq_ureg.kbd101_position)

    first_call_args = mock_connection.send_message_expect_reply.call_args_list[0]
    assert isinstance(first_call_args[0][0], AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE)

    second_call_args = mock_connection.send_message_expect_reply.call_args_list[1]
    assert isinstance(second_call_args[0][0], AptMessage_MGMSG_MOT_MOVE_ABSOLUTE)
    assert second_call_args[0][0].absolute_distance == 1000
    assert mock_connection.send_message_expect_reply.call_count == 2


def test_jog(mock_connection: Mock) -> None:
    def expect_reply(sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]):
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE):
            return make_ustatus(homed=True)
        if isinstance(sent_message, AptMessage_MGMSG_MOT_JOG):
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
        return None

    mock_connection.send_message_expect_reply.side_effect = expect_reply

    odl = OpticalDelayLineThorlabsKBD101(connection=mock_connection)
    odl.jog(JogDirection.FORWARD)

    # at least one expect-reply for jog
    assert any(isinstance(call[0][0], AptMessage_MGMSG_MOT_JOG) for call in mock_connection.send_message_expect_reply.call_args_list)


def test_get_velparams(mock_connection: Mock) -> None:
    def expect_reply(sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]):
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
        return None

    mock_connection.send_message_expect_reply.side_effect = expect_reply

    odl = OpticalDelayLineThorlabsKBD101(connection=mock_connection)
    velparams = odl.get_velparams()

    assert isinstance(velparams, OpticalDelayLineVelocityParams)
    assert velparams["minimum_velocity"].to("kbd101_velocity").magnitude == 1
    assert velparams["acceleration"].to("kbd101_acceleration").magnitude == 2
    assert velparams["maximum_velocity"].to("kbd101_velocity").magnitude == 3


def test_set_velparams(mock_connection: Mock) -> None:
    def send_no_reply(sent_message: AptMessage) -> None:
        assert isinstance(sent_message, AptMessage_MGMSG_MOT_SET_VELPARAMS)
        assert sent_message.chan_ident == ChanIdent(1)
        assert sent_message.destination == Address.GENERIC_USB
        assert sent_message.source == Address.HOST_CONTROLLER

    mock_connection.send_message_no_reply.side_effect = send_no_reply

    odl = OpticalDelayLineThorlabsKBD101(connection=mock_connection)
    odl.set_velparams(
        minimum_velocity=0 * pnpq_ureg.kbd101_velocity,
        acceleration=5 * pnpq_ureg.kbd101_acceleration,
        maximum_velocity=10 * pnpq_ureg.kbd101_velocity,
    )

    assert mock_connection.send_message_no_reply.call_count == 1


def test_get_homeparams(mock_connection: Mock) -> None:
    def expect_reply(sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]):
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_HOMEPARAMS):
            reply = AptMessage_MGMSG_MOT_GET_HOMEPARAMS(
                chan_ident=sent_message.chan_ident,
                destination=Address.HOST_CONTROLLER,
                source=Address.GENERIC_USB,
                home_direction=HomeDirection.FORWARD,
                limit_switch=LimitSwitch.HARDWARE_FORWARD,
                home_velocity=100,
                offset_distance=0,
            )
            assert match_reply_callback(reply)
            return reply
        return None

    mock_connection.send_message_expect_reply.side_effect = expect_reply

    odl = OpticalDelayLineThorlabsKBD101(connection=mock_connection)
    homeparams = odl.get_homeparams()

    assert isinstance(homeparams, OpticalDelayLineHomeParams)
    assert homeparams["home_velocity"].to("kbd101_velocity").magnitude == 100


def test_set_homeparams(mock_connection: Mock) -> None:
    def send_no_reply(sent_message: AptMessage) -> None:
        assert isinstance(sent_message, AptMessage_MGMSG_MOT_SET_HOMEPARAMS)
        assert sent_message.chan_ident == ChanIdent(1)

    mock_connection.send_message_no_reply.side_effect = send_no_reply

    odl = OpticalDelayLineThorlabsKBD101(connection=mock_connection)
    odl.set_homeparams(
        home_direction=HomeDirection.FORWARD,
        limit_switch=LimitSwitch.HARDWARE_FORWARD,
        home_velocity=200 * pnpq_ureg.kbd101_velocity,
        offset_distance=0 * pnpq_ureg.kbd101_position,
    )

    assert mock_connection.send_message_no_reply.call_count == 1


def test_get_jogparams(mock_connection: Mock) -> None:
    def expect_reply(sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]):
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_JOGPARAMS):
            reply = AptMessage_MGMSG_MOT_GET_JOGPARAMS(
                chan_ident=sent_message.chan_ident,
                destination=Address.HOST_CONTROLLER,
                source=Address.GENERIC_USB,
                jog_mode=JogMode.SINGLE_STEP,
                jog_step_size=20000,
                jog_minimum_velocity=1000,
                jog_acceleration=7,
                jog_maximum_velocity=1000,
                jog_stop_mode=StopMode.CONTROLLED,
            )
            assert match_reply_callback(reply)
            return reply
        return None

    mock_connection.send_message_expect_reply.side_effect = expect_reply

    odl = OpticalDelayLineThorlabsKBD101(connection=mock_connection)
    jogparams = odl.get_jogparams()
    assert isinstance(jogparams, OpticalDelayLineJogParams)
    assert jogparams["jog_step_size"].to("kbd101_position").magnitude == 20000


def test_set_jogparams(mock_connection: Mock) -> None:
    def send_no_reply(sent_message: AptMessage) -> None:
        assert isinstance(sent_message, AptMessage_MGMSG_MOT_SET_JOGPARAMS)
        assert sent_message.chan_ident == ChanIdent(1)

    mock_connection.send_message_no_reply.side_effect = send_no_reply

    odl = OpticalDelayLineThorlabsKBD101(connection=mock_connection)
    odl.set_jogparams(
        jog_mode=JogMode.SINGLE_STEP,
        jog_step_size=20000 * pnpq_ureg.kbd101_position,
        jog_minimum_velocity=1000 * pnpq_ureg.kbd101_velocity,
        jog_acceleration=7 * pnpq_ureg.kbd101_acceleration,
        jog_maximum_velocity=1000 * pnpq_ureg.kbd101_velocity,
        jog_stop_mode=StopMode.CONTROLLED,
    )

    assert mock_connection.send_message_no_reply.call_count == 1


def test_get_status(mock_connection: Mock) -> None:
    def expect_reply(sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]):
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE):
            return make_ustatus(homed=True)
        return None

    mock_connection.send_message_expect_reply.side_effect = expect_reply

    odl = OpticalDelayLineThorlabsKBD101(connection=mock_connection)
    status_msg = odl.get_status()
    assert isinstance(status_msg, AptMessage_MGMSG_MOT_GET_USTATUSUPDATE)

