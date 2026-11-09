"""Value Objects: invariantes (RN-01, RN-06, RN-10, RN-11)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.domain.shared import ValorInvalido
from src.domain.value_objects import (
    CambioFechaEntrega, CanalAutorizacion, ClienteId, DatosContacto, DatosRecepcion, Dinero, EstadoOrden, OrdenServicioId,
    EvidenciaAutorizacion, FechaEntrega, Kilometraje, NivelCombustible, Placas, Porcentaje, Vin,
)

T0 = datetime(2026, 11, 10, tzinfo=timezone.utc)


class TestDinero:
    def test_redondea_a_centavos_con_decimal(self):
        assert Dinero.de("10.005").monto == Decimal("10.01")

    def test_rechaza_float_y_negativos(self):
        with pytest.raises(ValorInvalido):
            Dinero(1.5)
        with pytest.raises(ValorInvalido):
            Dinero.de(-1)
        with pytest.raises(ValorInvalido):
            Dinero("abc")

    def test_aritmetica_y_orden(self):
        a, b = Dinero.de(100), Dinero.de("40.50")
        assert (a + b).monto == Decimal("140.50") and (a - b).monto == Decimal("59.50")
        assert b < a and a >= b and a.por(2) == Dinero.de(200)
        assert a.aplicar(Porcentaje.de(16)) == Dinero.de(16)
        assert Dinero.sumar([a, b]) == Dinero.de("140.50") and Dinero.cero() == Dinero.de(0)
        assert "100.00 MXN" in str(a)

    def test_resta_negativa_y_monedas_distintas(self):
        with pytest.raises(ValorInvalido):
            Dinero.de(1) - Dinero.de(2)
        with pytest.raises(ValorInvalido):
            Dinero.de(1) + Dinero.de(1, "USD")
        with pytest.raises(ValorInvalido):
            Dinero(1, "PESOS")
        with pytest.raises(ValorInvalido):
            Dinero.de(1).por(1.5)

    def test_es_inmutable(self):
        with pytest.raises(Exception):
            Dinero.de(1).monto = Decimal(2)  # type: ignore[misc]


class TestPorcentaje:
    def test_rango(self):
        assert Porcentaje.de(16).factor == Decimal("0.16")
        for malo in (-1, 101):
            with pytest.raises(ValorInvalido):
                Porcentaje.de(malo)
        with pytest.raises(ValorInvalido):
            Porcentaje(0.5)


class TestIdentificadores:
    def test_ids_son_str_con_prefijo_y_no_uuid(self):
        a, b = ClienteId.generar(), ClienteId.generar()
        assert isinstance(a.value, str) and a.value.startswith("CLI-") and a != b
        assert OrdenServicioId.generar().value.startswith("ORD-") and str(a) == a.value
        assert ClienteId.desde_str(str(a)) == a and ClienteId("CLI-001") == ClienteId.desde_str("CLI-001")
        assert ClienteId("X") != OrdenServicioId("X")                 # tipos distintos no se igualan

    def test_validacion(self):
        for malo in ("", " ", "con espacio", " x", "x" * 37):
            with pytest.raises(ValorInvalido):
                ClienteId.desde_str(malo)
        with pytest.raises(ValorInvalido):
            ClienteId(123)  # type: ignore[arg-type]


class TestContactoYVehiculo:
    def test_rn10_requiere_medio_digital(self):
        with pytest.raises(ValorInvalido):
            DatosContacto()
        with pytest.raises(ValorInvalido):
            DatosContacto(telefono="abc")
        with pytest.raises(ValorInvalido):
            DatosContacto(email="no-es-correo")
        assert DatosContacto(email="a@b.com").email == "a@b.com"

    def test_placas_y_vin(self):
        assert Placas(" abc 123 ").valor == "ABC123"
        with pytest.raises(ValorInvalido):
            Placas("!")
        assert Vin("1hgcm82633a004352").valor == "1HGCM82633A004352"
        with pytest.raises(ValorInvalido):
            Vin("OOO")

    def test_kilometraje(self):
        with pytest.raises(ValorInvalido):
            Kilometraje(-1)
        with pytest.raises(ValorInvalido):
            Kilometraje(True)  # type: ignore[arg-type]


class TestRecepcionYEvidencia:
    def test_rn01_motivo_obligatorio(self):
        with pytest.raises(ValorInvalido):
            DatosRecepcion(Kilometraje(1), NivelCombustible.LLENO, (), "  ")
        with pytest.raises(ValorInvalido):
            DatosRecepcion(Kilometraje(1), NivelCombustible.LLENO, ("",), "motivo")

    def test_rn11_evidencia(self):
        assert EvidenciaAutorizacion(T0, CanalAutorizacion.SMS, token_verificacion="t").canal is CanalAutorizacion.SMS
        with pytest.raises(ValorInvalido):                       # sin IP ni token
            EvidenciaAutorizacion(T0, CanalAutorizacion.WEB)
        with pytest.raises(ValorInvalido):                       # sin zona horaria
            EvidenciaAutorizacion(datetime(2026, 1, 1), CanalAutorizacion.WEB, ip="1.1.1.1")
        with pytest.raises(ValorInvalido):                       # IP inválida
            EvidenciaAutorizacion(T0, CanalAutorizacion.WEB, ip="999.1")


class TestFechas:
    def test_rn06_cambio_requiere_justificacion(self):
        a, b = FechaEntrega(T0), FechaEntrega(T0 + timedelta(days=1))
        assert CambioFechaEntrega(a, b, "Falta refacción", T0).nueva == b
        with pytest.raises(ValorInvalido):
            CambioFechaEntrega(a, b, " ", T0)
        with pytest.raises(ValorInvalido):
            CambioFechaEntrega(a, a, "igual", T0)

    def test_fecha_con_zona_y_vigencia(self):
        with pytest.raises(ValorInvalido):
            FechaEntrega(datetime(2026, 1, 1))
        assert FechaEntrega(T0).es_valida(T0 - timedelta(days=1)) and not FechaEntrega(T0).es_valida(T0 + timedelta(days=1))

    def test_estados_incluyen_cancelado(self):
        assert EstadoOrden.CANCELADO.value == "Cancelado"
