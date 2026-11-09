"""Recurso del catálogo del taller (servicio con capacidad, o refacción con existencia)."""
from __future__ import annotations

from decimal import Decimal

from ..shared import Entity, ReglaDeNegocioViolada, ValorInvalido
from ..value_objects import ConceptoId, Dinero, RecursoId
from .cotizacion import ConceptoCotizacion, TipoConcepto


class ItemCatalogo(Entity[RecursoId]):
    """Extensión del dominio (BRD §12 «inventario»): precio oficial y capacidad/stock del recurso."""

    def __init__(self, id: RecursoId, descripcion: str, precio: Dinero, capacidad: int,
                 habilitado: bool = True) -> None:
        super().__init__(id)
        if not descripcion or not descripcion.strip():
            raise ValorInvalido("La descripción del recurso es obligatoria")
        if precio.monto <= 0:
            raise ValorInvalido("El precio del recurso debe ser mayor a cero")
        if isinstance(capacidad, bool) or not isinstance(capacidad, int) or capacidad < 0:
            raise ValorInvalido("La capacidad/stock debe ser un entero >= 0")
        self._descripcion = descripcion.strip()
        self._precio = precio
        self._capacidad = capacidad
        self._habilitado = habilitado

    descripcion = property(lambda s: s._descripcion)
    precio = property(lambda s: s._precio)
    capacidad = property(lambda s: s._capacidad)
    habilitado = property(lambda s: s._habilitado)

    def habilitar(self) -> None:
        self._habilitado = True

    def deshabilitar(self) -> None:
        self._habilitado = False

    def validar_cantidad(self, cantidad: Decimal | int | str) -> Decimal:
        """Valida cantidad > 0, recurso habilitado y cantidad dentro de la capacidad."""
        cantidad = Decimal(str(cantidad))
        if cantidad <= 0:
            raise ValorInvalido(f"La cantidad de {self._id} debe ser mayor a cero")
        if not self._habilitado:
            raise ReglaDeNegocioViolada("CAT-01", f"El recurso {self._id} ({self._descripcion}) está deshabilitado")
        if cantidad > self._capacidad:
            raise ReglaDeNegocioViolada(
                "CAT-02", f"Cantidad {cantidad} excede la capacidad disponible ({self._capacidad}) de {self._id}")
        return cantidad

    def a_concepto(self, cantidad: Decimal | int | str,
                   tipo: TipoConcepto = TipoConcepto.MANO_DE_OBRA) -> ConceptoCotizacion:
        """Crea el concepto de cotización con el precio oficial del catálogo."""
        qty = self.validar_cantidad(cantidad)
        return ConceptoCotizacion(ConceptoId.generar(), tipo, self._descripcion, self._precio, qty, self._id)
