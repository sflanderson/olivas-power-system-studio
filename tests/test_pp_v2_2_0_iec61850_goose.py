"""
tests/test_pp_v2_2_0_iec61850_goose.py — v2.2.0 Sprint A.

Cobre IEC 61850-8-1 §17 GOOSE (Generic Object Oriented Substation
Event):

* GooseMessage dataclass (immutable)
* GoosePublisher.publish() em stub mode (registra em buffer)
* GooseSubscriber recebe via callback
* Time-critical: state change incrementa StNum + reset SqNum
"""

from __future__ import annotations

from datetime import datetime

import pytest


class TestGooseMessage:

    def test_module_loadable(self):
        from app.integration import iec61850_goose  # noqa: F401

    def test_message_dataclass(self):
        from app.integration.iec61850_goose import GooseMessage
        msg = GooseMessage(
            go_id="DEMO/LLN0$GO$gcb01",
            dataset="DEMO/LLN0$DS_TripCommand",
            st_num=1,
            sq_num=0,
            timestamp=datetime.now(),
            test=False,
            data={"trip": True},
        )
        assert msg.go_id == "DEMO/LLN0$GO$gcb01"
        assert msg.st_num == 1
        assert msg.test is False

    def test_message_immutable(self):
        from app.integration.iec61850_goose import GooseMessage
        msg = GooseMessage(
            go_id="X", dataset="X", st_num=0, sq_num=0,
            timestamp=datetime.now(), test=False, data={},
        )
        with pytest.raises(Exception):
            msg.st_num = 99


class TestGoosePublisher:

    def test_publisher_loadable(self):
        from app.integration.iec61850_goose import GoosePublisher
        assert GoosePublisher is not None

    def test_publisher_stub_mode(self):
        from app.integration.iec61850_goose import GoosePublisher
        pub = GoosePublisher(go_id="TEST/LLN0$GO$gcb01", mode="stub")
        # Estado inicial
        assert pub.st_num == 0
        assert pub.sq_num == 0

    def test_publish_state_change_increments_stnum(self):
        """Spec IEC 61850-8-1 §17.2.6: cada state change increment StNum + reset SqNum."""
        from app.integration.iec61850_goose import GoosePublisher
        pub = GoosePublisher(go_id="TEST/LLN0$GO$gcb01", mode="stub")
        # Publish state change
        msg1 = pub.publish_state_change(data={"trip": True})
        assert msg1.st_num == 1
        assert msg1.sq_num == 0

        # Outro state change → StNum incrementa, SqNum reset
        msg2 = pub.publish_state_change(data={"trip": False})
        assert msg2.st_num == 2
        assert msg2.sq_num == 0

    def test_publish_keep_alive_increments_sqnum(self):
        """Repetições keep-alive: incrementam SqNum, mantêm StNum."""
        from app.integration.iec61850_goose import GoosePublisher
        pub = GoosePublisher(go_id="TEST/LLN0$GO$gcb01", mode="stub")
        pub.publish_state_change(data={"trip": True})  # st=1, sq=0
        msg2 = pub.publish_keep_alive()  # st=1, sq=1
        assert msg2.st_num == 1
        assert msg2.sq_num == 1
        msg3 = pub.publish_keep_alive()
        assert msg3.sq_num == 2


class TestGooseSubscriber:

    def test_subscriber_loadable(self):
        from app.integration.iec61850_goose import GooseSubscriber
        assert GooseSubscriber is not None

    def test_subscriber_receives_via_callback(self):
        from app.integration.iec61850_goose import (
            GoosePublisher, GooseSubscriber,
        )
        received = []

        def on_message(msg):
            received.append(msg)

        sub = GooseSubscriber(
            go_id="TEST/LLN0$GO$gcb01",
            callback=on_message,
            mode="stub",
        )
        pub = GoosePublisher(go_id="TEST/LLN0$GO$gcb01", mode="stub")
        # Em stub mode, publicação direta para subscribers via
        # bus interno
        pub.connect_subscriber(sub)
        pub.publish_state_change(data={"trip": True})

        assert len(received) == 1
        assert received[0].data == {"trip": True}

    def test_subscriber_filters_by_go_id(self):
        """Subscriber só recebe mensagens do go_id que assinou."""
        from app.integration.iec61850_goose import (
            GoosePublisher, GooseSubscriber,
        )
        received = []
        sub = GooseSubscriber(
            go_id="OTHER/LLN0$GO$gcb02",
            callback=lambda m: received.append(m),
            mode="stub",
        )
        pub = GoosePublisher(go_id="TEST/LLN0$GO$gcb01", mode="stub")
        pub.connect_subscriber(sub)
        pub.publish_state_change(data={"trip": True})
        # Subscriber tem go_id diferente — não recebe
        assert len(received) == 0


class TestGooseRealMode:

    def test_real_mode_raises_without_lib(self):
        """Real mode requer libiec61850 — sem ela, raise informativo."""
        from app.integration.iec61850_goose import GoosePublisher
        pub = GoosePublisher(go_id="TEST", mode="real")
        with pytest.raises((NotImplementedError, ImportError, Exception)):
            pub.publish_state_change(data={"x": 1})
