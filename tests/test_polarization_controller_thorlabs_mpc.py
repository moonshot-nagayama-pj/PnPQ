from typing import Any, Callable
from unittest.mock import Mock, create_autospec

import pytest
from pint import Quantity

from pnpq.apt.connection import AptConnection
from pnpq.apt.protocol import (
    Address,
    AptMessage,
    AptMessage_MGMSG_MOT_GET_USTATUSUPDATE,
    AptMessage_MGMSG_MOT_MOVE_ABSOLUTE,
    AptMessage_MGMSG_MOT_MOVE_COMPLETED_6_BYTES,
    AptMessage_MGMSG_MOT_MOVE_JOG,
    AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE,
    AptMessage_MGMSG_POL_GET_PARAMS,
    AptMessage_MGMSG_POL_REQ_PARAMS,
    AptMessage_MGMSG_POL_SET_PARAMS,
    ChanIdent,
    JogDirection,
    UStatus,
    UStatusBits,
)
from pnpq.devices.polarization_controller_thorlabs_mpc import (
    PolarizationControllerParams,
    PolarizationControllerThorlabsMPC320,
)
from pnpq.errors import InvalidStateException
from pnpq.units import pnpq_ureg


@pytest.fixture(name="mock_connection", scope="function")
def mock_connection_fixture() -> Any:
    connection = create_autospec(AptConnection)
    connection.stop_event = Mock()
    connection.tx_ordered_sender_awaiting_reply = Mock()
    connection.tx_ordered_sender_awaiting_reply.is_set = Mock(return_value=True)
    yield connection

    # Shut down the polling thread
    def mock_send_message_unordered(message: AptMessage) -> None:
        raise InvalidStateException("Tried to use a closed AptConnection object.")

    connection.send_message_unordered.side_effect = mock_send_message_unordered


def test_move_absolute(mock_connection: Any) -> None:

    def mock_send_message_expect_reply(
        sent_message: AptMessage,
        match_reply_callback: Callable[[AptMessage], bool],
    ) -> None:
        if isinstance(sent_message, AptMessage_MGMSG_MOT_MOVE_ABSOLUTE):
            assert sent_message.absolute_distance == 10
            assert sent_message.chan_ident == ChanIdent(1)

            # A hypothetical reply message from the device
            reply_message = AptMessage_MGMSG_MOT_GET_USTATUSUPDATE(
                chan_ident=sent_message.chan_ident,
                position=sent_message.absolute_distance,
                velocity=50,
                motor_current=3 * pnpq_ureg.milliamp,
                status=UStatus.from_bits(UStatusBits.ACTIVE),
                destination=Address.HOST_CONTROLLER,
                source=Address.GENERIC_USB,
            )

            assert match_reply_callback(reply_message)

    mock_connection.send_message_expect_reply.side_effect = (
        mock_send_message_expect_reply
    )

    controller = PolarizationControllerThorlabsMPC320(connection=mock_connection)

    controller.move_absolute(ChanIdent(1), 10 * pnpq_ureg.mpc320_step)

    # Two calls for enabling and disabling the channel, one call for moving the motor
    assert mock_connection.send_message_expect_reply.call_count == 3


def test_jog(mock_connection: Any) -> None:
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

            assert match_reply_callback(reply_message)

    mock_connection.send_message_expect_reply.side_effect = (
        mock_send_message_expect_reply
    )

    controller = PolarizationControllerThorlabsMPC320(connection=mock_connection)

    controller.jog(ChanIdent(1), jog_direction=JogDirection.FORWARD)

    # Two calls for enabling and disabling the channel, one call for jogging the motor
    assert mock_connection.send_message_expect_reply.call_count == 3


@pytest.mark.parametrize(
    "invalid_angle",
    [
        -10 * pnpq_ureg.degree,
        180 * pnpq_ureg.degree,
    ],
)
def test_invalid_angle_inputs(mock_connection: Any, invalid_angle: Quantity) -> None:
    controller = PolarizationControllerThorlabsMPC320(connection=mock_connection)

    with pytest.raises(ValueError):
        controller.move_absolute(ChanIdent(1), invalid_angle)


def test_get_params(mock_connection: Any) -> None:
    def mock_send_message_expect_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> AptMessage_MGMSG_POL_GET_PARAMS:

        assert isinstance(sent_message, AptMessage_MGMSG_POL_REQ_PARAMS)

        reply_message = AptMessage_MGMSG_POL_GET_PARAMS(
            destination=Address.HOST_CONTROLLER,
            source=Address.GENERIC_USB,
            velocity=1,
            home_position=2,
            jog_step_1=3,
            jog_step_2=4,
            jog_step_3=5,
        )

        assert match_reply_callback(reply_message)
        return reply_message

    mock_connection.send_message_expect_reply.side_effect = (
        mock_send_message_expect_reply
    )

    controller = PolarizationControllerThorlabsMPC320(connection=mock_connection)

    params: PolarizationControllerParams = controller.get_params()

    assert params == {
        "velocity": 1 * pnpq_ureg.mpc320_velocity,
        "home_position": 2 * pnpq_ureg.mpc320_step,
        "jog_step_1": 3 * pnpq_ureg.mpc320_step,
        "jog_step_2": 4 * pnpq_ureg.mpc320_step,
        "jog_step_3": 5 * pnpq_ureg.mpc320_step,
    }

    assert mock_connection.send_message_expect_reply.call_count == 1


def test_set_params(mock_connection: Any) -> None:

    # Mock the reply for send_message_expect_reply, which is called in self.get_params()
    def mock_get_params_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> AptMessage_MGMSG_POL_GET_PARAMS:

        assert isinstance(sent_message, AptMessage_MGMSG_POL_REQ_PARAMS)

        reply_message = AptMessage_MGMSG_POL_GET_PARAMS(
            destination=Address.HOST_CONTROLLER,
            source=Address.GENERIC_USB,
            velocity=1,
            home_position=2,
            jog_step_1=3,
            jog_step_2=4,
            jog_step_3=5,
        )

        assert match_reply_callback(reply_message)
        return reply_message

    mock_connection.send_message_expect_reply.side_effect = mock_get_params_reply

    def mock_send_message_no_reply(sent_message: AptMessage) -> None:

        assert isinstance(sent_message, AptMessage_MGMSG_POL_SET_PARAMS)
        assert sent_message.destination == Address.GENERIC_USB
        assert sent_message.source == Address.HOST_CONTROLLER
        assert sent_message.velocity == 1
        assert sent_message.home_position == 2
        assert sent_message.jog_step_1 == 3
        assert sent_message.jog_step_2 == 4
        assert sent_message.jog_step_3 == 5

    # Mock the reply for send_message_no_reply, which is called in self.set_params()
    mock_connection.send_message_no_reply.side_effect = mock_send_message_no_reply

    controller = PolarizationControllerThorlabsMPC320(connection=mock_connection)

    params = {
        "velocity": 1 * pnpq_ureg.mpc320_velocity,
        "home_position": 2 * pnpq_ureg.mpc320_step,
        "jog_step_1": 3 * pnpq_ureg.mpc320_step,
        "jog_step_2": 4 * pnpq_ureg.mpc320_step,
        "jog_step_3": 5 * pnpq_ureg.mpc320_step,
    }

    controller.set_params(**params)

    assert mock_connection.send_message_no_reply.call_count == 1
    assert mock_connection.send_message_expect_reply.call_count == 1


def test_get_status(mock_connection: Any) -> None:

    # A hypothetical reply message from the device
    reply_message = AptMessage_MGMSG_MOT_GET_USTATUSUPDATE(
        chan_ident=ChanIdent(1),
        position=10,
        velocity=0,
        motor_current=0 * pnpq_ureg.milliamp,
        status=UStatus.from_bits(UStatusBits.ACTIVE),
        destination=Address.HOST_CONTROLLER,
        source=Address.GENERIC_USB,
    )

    def mock_send_message_expect_reply(
        sent_message: AptMessage, match_reply_callback: Callable[[AptMessage], bool]
    ) -> AptMessage:

        assert isinstance(sent_message, AptMessage_MGMSG_MOT_REQ_USTATUSUPDATE)
        assert sent_message.chan_ident == ChanIdent(1)
        assert match_reply_callback(reply_message)

        return reply_message

    mock_connection.send_message_expect_reply.side_effect = (
        mock_send_message_expect_reply
    )

    controller = PolarizationControllerThorlabsMPC320(connection=mock_connection)

    status: AptMessage_MGMSG_MOT_GET_USTATUSUPDATE = controller.get_status(ChanIdent(1))

    assert status == reply_message

    assert mock_connection.send_message_expect_reply.call_count == 1
