from typing import Any, Any, Callable
from unittest.mock import Mock, create_autospec

import pytest

import pytest
import structlog

from pnpq.apt.connection import AptConnection
from pnpq.apt.protocol import (
    Address,
    AptMessage,
    AptMessage_MGMSG_MOT_GET_STATUSUPDATE,
    AptMessage_MGMSG_MOT_GET_VELPARAMS,
    AptMessage_MGMSG_MOT_MOVE_ABSOLUTE,
    AptMessage_MGMSG_MOT_MOVE_COMPLETED_20_BYTES,
    AptMessage_MGMSG_MOT_MOVE_COMPLETED_6_BYTES,
    AptMessage_MGMSG_MOT_MOVE_JOG,
    AptMessage_MGMSG_MOT_REQ_VELPARAMS,
    AptMessage_MGMSG_POL_GET_PARAMS,
    AptMessage_MGMSG_POL_REQ_PARAMS,
    AptMessage_MGMSG_MOT_REQ_STATUSUPDATE,
    ChanIdent,
    JogDirection,
    Status,
    UStatus,
)
from pnpq.devices.waveplate_thorlabs_k10cr1 import WaveplateThorlabsK10CR1, WaveplateVelocityParams
from pnpq.units import pnpq_ureg


@pytest.fixture(name="mock_connection", scope="function")
def mock_connection_fixture() -> Mock:
    connection = create_autospec(AptConnection)
    connection.stop_event = Mock()
    connection.tx_ordered_sender_awaiting_reply = Mock()
    connection.tx_ordered_sender_awaiting_reply.is_set = Mock(return_value=True)
    assert isinstance(connection, Mock)
    return connection


def test_move_absolute(mock_connection: Any) -> None:
    ustatus_message = AptMessage_MGMSG_MOT_GET_STATUSUPDATE(
        chan_ident=ChanIdent(1),
        destination=Address.HOST_CONTROLLER,
        source=Address.GENERIC_USB,
        enc_count=0,
        position=0,
        status=Status(INMOTIONCCW=True, INMOTIONCW=True, HOMED=True),
    )

    def mock_send_message_expect_reply(
        sent_message: AptMessage,
        match_reply_callback: Callable[
            [
                AptMessage,
            ],
            bool,
        ],
    ) -> AptMessage | None:
        if isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_STATUSUPDATE):
            return ustatus_message

        if isinstance(sent_message, AptMessage_MGMSG_MOT_MOVE_ABSOLUTE):
            assert sent_message.absolute_distance == 10
            assert sent_message.chan_ident == ChanIdent(1)

            # A hypothetical reply message from the device
            reply_message = AptMessage_MGMSG_MOT_MOVE_COMPLETED_20_BYTES(
                chan_ident=sent_message.chan_ident,
                position=sent_message.absolute_distance,
                velocity=0,
                destination=Address.HOST_CONTROLLER,
                source=Address.GENERIC_USB,
                motor_current=0 * pnpq_ureg.milliamp,
                status=UStatus(INMOTIONCCW=True, INMOTIONCW=True, ENABLED=True),
            )

            assert 3 == 4
            assert match_reply_callback(reply_message)
        return None

    mock_connection.send_message_expect_reply.side_effect = (
        mock_send_message_expect_reply
    )

    controller = WaveplateThorlabsK10CR1(connection=mock_connection)

    controller.move_absolute(10 * pnpq_ureg.k10cr1_step)

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

    # One call for moving the motor.
    # Enabling and disabling the channel doesn't use an expect reply in K10CR1
    # Second call for getting the status update to check if the device is homed
    assert mock_connection.send_message_expect_reply.call_count == 2



log = structlog.get_logger()


def test_velparams(mock_connection: Any) -> None:
    def mock_send_message_expect_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> None:
        if isinstance(sent_message, AptMessage_MGMSG_MOT_MOVE_JOG):
            assert sent_message.chan_ident == ChanIdent(1)
            assert sent_message.jog_direction == JogDirection.FORWARD

            # A hypothetical reply message from the device
            reply_message = AptMessage_MGMSG_MOT_MOVE_COMPLETED_6_BYTES(
                chan_ident=sent_message.chan_ident,
                destination=Address.HOST_CONTROLLER,
                source=Address.GENERIC_USB,
            )

            assert 3 == 4
            assert match_reply_callback(reply_message)
        return None

    mock_connection.send_message_expect_reply.side_effect = (
        mock_send_message_expect_reply
    )

    ustatus_message = AptMessage_MGMSG_MOT_GET_STATUSUPDATE(
        chan_ident=ChanIdent(1),
        destination=Address.HOST_CONTROLLER,
        source=Address.GENERIC_USB,
        enc_count=0,
        position=0,
        status=Status(INMOTIONCCW=True, INMOTIONCW=True, HOMED=True),
    )

    mock_connection.send_message_expect_reply.side_effect = [
        ustatus_message,
        mock_send_message_expect_reply,
    ]
    mock_connection.tx_ordered_sender_awaiting_reply = Mock()
    mock_connection.tx_ordered_sender_awaiting_reply.is_set = Mock(return_value=True)

    controller = WaveplateThorlabsK10CR1(connection=mock_connection)
    controller = WaveplateThorlabsK10CR1(connection=mock_connection)

    controller.move_absolute(10 * pnpq_ureg.k10cr1_step)

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

    # One call for moving the motor.
    # Enabling and disabling the channel doesn't use an expect reply in K10CR1
    # Second call for getting the status update to check if the device is homed
    assert mock_connection.send_message_expect_reply.call_count == 2
    assert mock_connection.send_message_expect_reply.call_count == 2




# def test_set_params(mock_connection: Any) -> None:

#     # Mock the reply for send_message_expect_reply, which is called in self.get_params()
#     def mock_get_params_reply(
#         sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
#     ) -> AptMessage_MGMSG_POL_GET_PARAMS:

#         assert isinstance(sent_message, AptMessage_MGMSG_POL_REQ_PARAMS)

#         reply_message = AptMessage_MGMSG_POL_GET_PARAMS(
#             destination=Address.HOST_CONTROLLER,
#             source=Address.GENERIC_USB,
#             velocity=1,
#             home_position=2,
#             jog_step_1=3,
#             jog_step_2=4,
#             jog_step_3=5,
#         )

#         assert match_reply_callback(reply_message)
#         return reply_message

#     mock_connection.send_message_expect_reply.side_effect = mock_get_params_reply

#     def mock_send_message_no_reply(sent_message: AptMessage) -> None:

#         assert isinstance(sent_message, AptMessage_MGMSG_POL_SET_PARAMS)
#         assert sent_message.destination == Address.GENERIC_USB
#         assert sent_message.source == Address.HOST_CONTROLLER
#         assert sent_message.velocity == 1
#         assert sent_message.home_position == 2
#         assert sent_message.jog_step_1 == 3
#         assert sent_message.jog_step_2 == 4
#         assert sent_message.jog_step_3 == 5

#     # Mock the reply for send_message_no_reply, which is called in self.set_params()
#     mock_connection.send_message_no_reply.side_effect = mock_send_message_no_reply

#     controller = PolarizationControllerThorlabsMPC320(connection=mock_connection)

#     params = {
#         "velocity": 1 * pnpq_ureg.mpc320_velocity,
#         "home_position": 2 * pnpq_ureg.mpc320_step,
#         "jog_step_1": 3 * pnpq_ureg.mpc320_step,
#         "jog_step_2": 4 * pnpq_ureg.mpc320_step,
#         "jog_step_3": 5 * pnpq_ureg.mpc320_step,
#     }

#     controller.set_params(**params)

#     assert mock_connection.send_message_no_reply.call_count == 1
#     assert mock_connection.send_message_expect_reply.call_count == 1


# def test_get_status(mock_connection: Any) -> None:

#     # A hypothetical reply message from the device
#     reply_message = AptMessage_MGMSG_MOT_GET_USTATUSUPDATE(
#         chan_ident=ChanIdent(1),
#         position=10,
#         velocity=0,
#         motor_current=0 * pnpq_ureg.milliamp,
#         status=UStatus.from_bits(UStatusBits.ACTIVE),
#         destination=Address.HOST_CONTROLLER,
#         source=Address.GENERIC_USB,
#     )

#     def mock_send_message_expect_reply(
#         sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
#     ) -> AptMessage:

#         assert isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE)
#         assert sent_message.chan_ident == ChanIdent(1)
#         assert match_reply_callback(reply_message)

#         return reply_message

#     mock_connection.send_message_expect_reply.side_effect = (
#         mock_send_message_expect_reply
#     )

#     controller = PolarizationControllerThorlabsMPC320(connection=mock_connection)

#     status: AptMessage_MGMSG_MOT_GET_USTATUSUPDATE = controller.get_status(ChanIdent(1))

#     assert status == reply_message

#     assert mock_connection.send_message_expect_reply.call_count == 1
