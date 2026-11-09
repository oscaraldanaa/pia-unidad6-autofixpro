"""Esquemas de entrada (Pydantic) con ejemplos para Swagger UI."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IdOut(BaseModel):
    id: str = Field(description="Identificador (texto) de la entidad creada, p. ej. CLI-9F2C41AB07D3E856")


class ClienteIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    telefono: str | None = Field(None, description="Para SMS (RN-10)")
    email: str | None = None
    cuenta_flotilla_id: str | None = None
    activo: bool = True
    es_preferente: bool = Field(False, description="Cliente preferente (VIP); extensión para beneficio_referencia")
    model_config = ConfigDict(json_schema_extra={"example": {
        "nombre": "Ana López", "telefono": "8112345678", "email": "ana@example.com"}})


class VehiculoIn(BaseModel):
    placas: str
    marca: str
    modelo: str
    kilometraje: int = Field(ge=0)
    vin: str | None = Field(None, description="17 caracteres, sin I, O, Q")
    cuenta_flotilla_id: str | None = None
    model_config = ConfigDict(json_schema_extra={"example": {
        "placas": "ABC-123", "marca": "Nissan", "modelo": "Versa", "kilometraje": 50000}})


class TecnicoIn(BaseModel):
    nombre: str
    especialidad: str
    model_config = ConfigDict(json_schema_extra={"example": {"nombre": "Luis Pérez", "especialidad": "Frenos"}})


class FlotillaIn(BaseModel):
    razon_social: str
    autorizador_corporativo_id: str = Field(description="ID de un cliente ya registrado")
    descuento_pct: Decimal = Field(Decimal(0), ge=0, le=100)
    prioridad: int = Field(0, ge=0)
    dias_credito: int = Field(0, ge=0)


class EstadoClienteIn(BaseModel):
    activo: bool


class ItemCatalogoIn(BaseModel):
    descripcion: str = Field(min_length=1)
    precio_mxn: Decimal = Field(gt=0, decimal_places=2)
    capacidad: int = Field(ge=0, description="Capacidad de servicio o existencia en inventario")
    habilitado: bool = True
    model_config = ConfigDict(json_schema_extra={"example": {
        "descripcion": "Frenos 02", "precio_mxn": "430.00", "capacidad": 16, "habilitado": True}})


class IngresoIn(BaseModel):
    cliente_id: str
    vehiculo_id: str
    kilometraje: int = Field(ge=0)
    combustible: Literal["vacio", "1/4", "1/2", "3/4", "lleno"]
    motivo_ingreso: str = Field(min_length=1)
    danos_visibles: list[str] = Field(default_factory=list)
    promocion_activa: bool = Field(False, description="Promoción vigente en la operación (extensión; usada por beneficio_referencia)")
    model_config = ConfigDict(json_schema_extra={"example": {
        "cliente_id": "<id>", "vehiculo_id": "<id>", "kilometraje": 50100, "combustible": "1/2",
        "motivo_ingreso": "Ruido al frenar", "danos_visibles": ["Rayón en puerta derecha"]}})


class DiagnosticoIn(BaseModel):
    tecnico_id: str
    hallazgos: list[str] = Field(min_length=1)


class ConceptoIn(BaseModel):
    """Concepto libre (``descripcion`` + ``precio_unitario``) o de catálogo (``recurso_id``).

    Con ``recurso_id`` se usa el precio oficial y se valida que el recurso esté habilitado y que la
    cantidad no exceda su capacidad (409 CAT-01 / CAT-02; 404 si no existe)."""

    tipo: Literal["mano_de_obra", "refaccion"] = "mano_de_obra"
    descripcion: str | None = Field(None, min_length=1)
    precio_unitario: Decimal | None = Field(None, gt=0, decimal_places=2)
    cantidad: Decimal = Field(Decimal(1), gt=0)
    recurso_id: str | None = None

    @model_validator(mode="after")
    def _libre_o_catalogo(self):
        if not self.recurso_id and (not self.descripcion or self.precio_unitario is None):
            raise ValueError("Indique recurso_id o (descripcion y precio_unitario)")
        return self


class CotizacionIn(BaseModel):
    conceptos: list[ConceptoIn] = Field(min_length=1)
    model_config = ConfigDict(json_schema_extra={"example": {"conceptos": [
        {"tipo": "mano_de_obra", "descripcion": "Cambio de balatas", "precio_unitario": "500.00"},
        {"tipo": "refaccion", "descripcion": "Balatas delanteras", "precio_unitario": "800.50", "cantidad": "1"}]}})


class RespuestaIn(BaseModel):
    """Decisión del cliente por concepto (RN-05). La IP y el sello de tiempo los captura el servidor (RN-11)."""

    decisiones: dict[str, bool] = Field(description="concepto_id -> true (autoriza) / false (rechaza)")
    canal: Literal["sms", "email", "web"] = "web"
    token_verificacion: str | None = None
    model_config = ConfigDict(json_schema_extra={"example": {
        "decisiones": {"<concepto_id_1>": True, "<concepto_id_2>": False}, "canal": "web"}})


class AsignacionIn(BaseModel):
    tecnico_id: str


class RefaccionFaltanteIn(BaseModel):
    concepto_id: str
    reposicion_estimada: datetime | None = None


class ReposicionIn(BaseModel):
    nueva_fecha: datetime
    motivo: str = Field(min_length=1)


class FallaIn(BaseModel):
    tecnico_id: str
    descripcion: str = Field(min_length=1)


class FechaEntregaIn(BaseModel):
    fecha_estimada: datetime = Field(description="Con zona horaria, p. ej. 2026-11-20T18:00:00Z")
    justificacion: str | None = Field(None, description="Obligatoria si ya existía una fecha (RN-06)")


class CobroIn(BaseModel):
    monto: Decimal = Field(gt=0, decimal_places=2, description="Debe igualar el total autorizado")


class CancelacionIn(BaseModel):
    motivo: str = Field(min_length=1)
