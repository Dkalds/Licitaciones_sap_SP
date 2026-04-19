"""Estado de filtros del sidebar — dataclass serializable a session_state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class FiltersState:
    q: str = ""
    rango: tuple[date, date] | None = None
    estados: list[str] = field(default_factory=list)
    ccaas: list[str] = field(default_factory=list)
    organos: list[str] = field(default_factory=list)
    tipos_proy: list[str] = field(default_factory=list)
    importe_min: int = 0

    def is_active(self) -> bool:
        """Devuelve True si algún filtro distinto al rango está activo."""
        return bool(
            self.q
            or self.estados
            or self.ccaas
            or self.organos
            or self.tipos_proy
            or self.importe_min > 0
        )

    def active_labels(self) -> list[str]:
        """Lista de etiquetas de filtros activos (para chips de la UI)."""
        labels = []
        if self.q:
            labels.append(f'🔍 "{self.q}"')
        for e in self.estados:
            labels.append(f"Estado: {e}")
        for c in self.ccaas:
            labels.append(f"CCAA: {c}")
        for o in self.organos:
            labels.append(f"Órgano: {o[:30]}")
        for t in self.tipos_proy:
            labels.append(f"Tipo: {t}")
        if self.importe_min > 0:
            labels.append(f"Imp. mín: {self.importe_min:,} €")
        return labels

    def to_query_params(self) -> dict[str, str]:
        """Serializa el estado activo a parámetros de URL (solo campos con valor)."""
        params: dict[str, str] = {}
        if self.q:
            params["q"] = self.q
        if self.rango:
            params["fecha_desde"] = self.rango[0].isoformat()
            params["fecha_hasta"] = self.rango[1].isoformat()
        if self.estados:
            params["estados"] = ",".join(self.estados)
        if self.ccaas:
            params["ccaas"] = ",".join(self.ccaas)
        if self.organos:
            params["organos"] = ",".join(self.organos)
        if self.tipos_proy:
            params["tipos"] = ",".join(self.tipos_proy)
        if self.importe_min > 0:
            params["imp_min"] = str(self.importe_min)
        return params

    @classmethod
    def from_query_params(cls, params: dict[str, str]) -> FiltersState:
        """Reconstruye un FiltersState desde parámetros de URL."""
        rango = None
        if "fecha_desde" in params and "fecha_hasta" in params:
            try:
                rango = (
                    date.fromisoformat(params["fecha_desde"]),
                    date.fromisoformat(params["fecha_hasta"]),
                )
            except ValueError:
                pass
        try:
            importe_min = int(params.get("imp_min") or 0)
        except (ValueError, TypeError):
            importe_min = 0
        return cls(
            q=params.get("q", ""),
            rango=rango,
            estados=[e for e in params.get("estados", "").split(",") if e],
            ccaas=[c for c in params.get("ccaas", "").split(",") if c],
            organos=[o for o in params.get("organos", "").split(",") if o],
            tipos_proy=[t for t in params.get("tipos", "").split(",") if t],
            importe_min=importe_min,
        )
