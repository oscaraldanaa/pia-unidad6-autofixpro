"""Excepciones del dominio. No dependen de ningún framework."""


class DomainError(Exception):
    """Error base de la capa de dominio."""


class ValorInvalido(DomainError):
    """Un Value Object o atributo viola su invariante de construcción."""


class ReglaDeNegocioViolada(DomainError):
    """Se intentó una operación que viola una regla del BRD (RN-xx)."""

    def __init__(self, regla: str, mensaje: str) -> None:
        super().__init__(f"[{regla}] {mensaje}")
        self.regla = regla
        self.mensaje = mensaje


class EntidadNoEncontrada(DomainError):
    """No existe la entidad solicitada (la capa API la traduce a 404)."""
