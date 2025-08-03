from typing import Any, Callable
from unittest.mock import Mock, create_autospec

import pytest
import structlog

from pnpq.apt.connection import AptConnection
from pnpq.apt.protocol import (
    Address,
    AptMessage,
    AptMessage_MGMSG_MOT_GET_STATUSUPDATE,
    AptMessage_MGMSG_MOT_MOVE_ABSOLUTE,
    AptMessage_MGMSG_MOT_MOVE_COMPLETED_20_BYTES,
    AptMessage_MGMSG_MOT_REQ_STATUSUPDATE,
    ChanIdent,
    Status,
    UStatus,
)
from pnpq.devices.waveplate_thorlabs_k10cr1 import WaveplateThorlabsK10CR1
from pnpq.units import pnpq_ureg


@pytest.fixture(name="mock_connection", scope="function")
def mock_connection_fixture() -> Any:
    connection = create_autospec(AptConnection)
    connection.stop_event = Mock()
    connection.tx_ordered_sender_awaiting_reply = Mock()
    connection.tx_ordered_sender_awaiting_reply.is_set = Mock(return_value=True)
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
    ) -> None:
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

            assert match_reply_callback(reply_message)

    def dynamic_mock() -> Callable[..., Any]:
        call_count = 0

        def side_effect(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                return ustatus_message
            if call_count == 2:
                return mock_send_message_expect_reply(*args, **kwargs)
            raise RuntimeError("Unexpected call count")

        return side_effect

    mock_connection.send_message_expect_reply.side_effect = dynamic_mock()

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
