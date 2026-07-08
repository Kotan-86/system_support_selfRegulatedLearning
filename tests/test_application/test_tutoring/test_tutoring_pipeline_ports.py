# 仕様: docs/spec/application-usecase.md#RunTutoringPipeline
"""ITS 3 段パイプライン Port の契約検証。"""
from __future__ import annotations

import inspect

from application.tutoring.ports.interface_model_gateway import InterfaceModelGateway
from application.tutoring.ports.pedagogical_model_gateway import PedagogicalModelGateway
from application.tutoring.ports.student_model_gateway import StudentModelGateway
from tests.test_application.fakes.tutoring.fake_interface_model_gateway import (
    FakeInterfaceModelGateway,
)
from tests.test_application.fakes.tutoring.fake_pedagogical_model_gateway import (
    FakePedagogicalModelGateway,
)
from tests.test_application.fakes.tutoring.fake_student_model_gateway import (
    FakeStudentModelGateway,
)


class TestTutoringPipelinePortContracts:
    """Fake 3 Gateway が Port ABC を満たすことを検証する。"""

    def test_fake_student_model_gateway_is_student_model_gateway(self) -> None:
        gateway = FakeStudentModelGateway()
        assert isinstance(gateway, StudentModelGateway)

    def test_fake_pedagogical_model_gateway_is_pedagogical_model_gateway(self) -> None:
        gateway = FakePedagogicalModelGateway()
        assert isinstance(gateway, PedagogicalModelGateway)

    def test_fake_interface_model_gateway_is_interface_model_gateway(self) -> None:
        gateway = FakeInterfaceModelGateway()
        assert isinstance(gateway, InterfaceModelGateway)

    def test_student_model_gateway_declares_interpret(self) -> None:
        methods = {
            name
            for name, member in inspect.getmembers(StudentModelGateway)
            if getattr(member, "__isabstractmethod__", False)
        }
        assert methods == {"interpret"}

    def test_pedagogical_model_gateway_declares_select_move(self) -> None:
        methods = {
            name
            for name, member in inspect.getmembers(PedagogicalModelGateway)
            if getattr(member, "__isabstractmethod__", False)
        }
        assert methods == {"select_move"}

    def test_interface_model_gateway_declares_generate(self) -> None:
        methods = {
            name
            for name, member in inspect.getmembers(InterfaceModelGateway)
            if getattr(member, "__isabstractmethod__", False)
        }
        assert methods == {"generate"}
