"""
Taxonomia de mapas de calibração ECU.
Categorias, nomes típicos, unidades e níveis Guardian.
Mapas de emissão/imobilizador/odômetro são Guardian 4 (legal/regulatório).
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MapCategory(str, Enum):
    FUELING      = "fueling"
    IGNITION     = "ignition"
    BOOST        = "boost"
    TORQUE_MODEL = "torque_model"
    LIMITERS     = "limiters"
    LAMBDA       = "lambda"
    PEDAL        = "pedal"
    COOLING      = "cooling"
    EMISSION     = "emission"     # Guardian 4 — legal
    IMMOBILIZER  = "immobilizer"  # Guardian 4 — legal
    ODOMETER     = "odometer"     # Guardian 4 — legal
    DIAGNOSTIC   = "diagnostic"
    OTHER        = "other"


_CATEGORY_GUARDIAN_LEVEL: dict[MapCategory, int] = {
    MapCategory.FUELING:      2,
    MapCategory.IGNITION:     2,
    MapCategory.BOOST:        2,
    MapCategory.TORQUE_MODEL: 2,
    MapCategory.LIMITERS:     3,
    MapCategory.LAMBDA:       2,
    MapCategory.PEDAL:        2,
    MapCategory.COOLING:      2,
    MapCategory.EMISSION:     4,
    MapCategory.IMMOBILIZER:  4,
    MapCategory.ODOMETER:     4,
    MapCategory.DIAGNOSTIC:   3,
    MapCategory.OTHER:        2,
}


@dataclass
class MapDefinition:
    name: str
    category: MapCategory
    description: str
    unit: str
    axes: list[str]
    typical_range: tuple[float, float]
    safety_note: str = ""
    source: str = "knowledge_base"

    @property
    def guardian_level(self) -> int:
        return _CATEGORY_GUARDIAN_LEVEL[self.category]

    @property
    def requires_legal_note(self) -> bool:
        return self.guardian_level >= 4

    def summary_line(self) -> str:
        icon = "⚠️  LEGAL" if self.requires_legal_note else ("⚠️" if self.guardian_level >= 3 else "")
        return f"[{self.category.value}] {self.name} ({self.unit}) {icon}".strip()


_KNOWN_MAPS: list[MapDefinition] = [
    # Injeção
    MapDefinition("injection_quantity_base", MapCategory.FUELING,
        "Quantidade de injeção de base (mg/stk) por RPM e carga",
        "mg/stk", ["rpm", "charge_mg_stk"], (0.0, 150.0),
        "Excesso pode danificar catalisador/turbo."),
    MapDefinition("injection_time_ms", MapCategory.FUELING,
        "Tempo de injeção em ms por RPM e pressão de rail",
        "ms", ["rpm", "rail_pressure_bar"], (0.5, 20.0)),
    MapDefinition("rail_pressure_setpoint", MapCategory.FUELING,
        "Pressão de rail desejada (bar) por RPM e carga",
        "bar", ["rpm", "charge_mg_stk"], (200.0, 2000.0),
        "Exceder limites do injector pode causar falha catastrófica."),
    # Ignição
    MapDefinition("ignition_advance_base", MapCategory.IGNITION,
        "Avanço de ignição base (graus) por RPM e carga",
        "deg BTDC", ["rpm", "charge_mg_stk"], (-10.0, 45.0),
        "Avanço excessivo causa detonação; atraso excessivo superaquece catalisador."),
    MapDefinition("knock_retard_map", MapCategory.IGNITION,
        "Retardo máximo por batida (graus) por cilindro",
        "deg", ["cylinder"], (-20.0, 0.0)),
    # Turbo
    MapDefinition("boost_pressure_setpoint", MapCategory.BOOST,
        "Pressão de turbo desejada (mbar absoluto) por RPM e carga",
        "mbar", ["rpm", "charge_mg_stk"], (900.0, 2800.0),
        "Exceder pressão máxima do turbo pode causar falha mecânica."),
    MapDefinition("wastegate_duty_cycle", MapCategory.BOOST,
        "Ciclo de trabalho da wastegate (%) por RPM e pressão alvo",
        "%", ["rpm", "boost_setpoint_mbar"], (0.0, 100.0)),
    # Modelo de torque
    MapDefinition("torque_model_combustion_requested", MapCategory.TORQUE_MODEL,
        "Torque de combustão solicitado (Nm) por RPM e posição do pedal",
        "Nm", ["rpm", "pedal_percent"], (0.0, 600.0)),
    MapDefinition("torque_limit_engine", MapCategory.TORQUE_MODEL,
        "Limite máximo de torque do motor (Nm) por RPM",
        "Nm", ["rpm"], (0.0, 600.0),
        "Aumentar além da capacidade mecânica pode causar falha de transmissão."),
    # Limitadores
    MapDefinition("rpm_limiter_hard_cut", MapCategory.LIMITERS,
        "RPM máximo com corte duro de combustível",
        "rpm", [], (4000.0, 10000.0),
        "⚠️ Remover limitador sem conhecer limite mecânico do motor/câmbio é risco alto."),
    MapDefinition("speed_limiter_setpoint", MapCategory.LIMITERS,
        "Limite de velocidade (km/h)",
        "km/h", [], (0.0, 300.0),
        "Pode ter implicações legais dependendo da finalidade do veículo."),
    # Lambda
    MapDefinition("lambda_setpoint_base", MapCategory.LAMBDA,
        "Lambda desejado (stoich = 1.0) por RPM e carga",
        "lambda", ["rpm", "charge_mg_stk"], (0.7, 1.4)),
    MapDefinition("lambda_enrichment_wot", MapCategory.LAMBDA,
        "Enriquecimento WOT (lambda alvo em plena carga)",
        "lambda", ["rpm"], (0.75, 1.0)),
    # Pedal
    MapDefinition("pedal_map_driver_demand", MapCategory.PEDAL,
        "Curva de demanda do motorista: pedal (%) → torque solicitado (%)",
        "%", ["pedal_percent", "rpm"], (0.0, 100.0)),
    # Emissões — Guardian 4
    MapDefinition("egr_rate_setpoint", MapCategory.EMISSION,
        "Taxa de EGR desejada (%) por RPM e carga",
        "%", ["rpm", "charge_mg_stk"], (0.0, 60.0),
        "⚠️ LEGAL: altera emissões reguladas (NOx). Autorização do titular obrigatória."),
    MapDefinition("dpf_regen_temperature", MapCategory.EMISSION,
        "Temperatura de regeneração do DPF (°C)",
        "°C", ["dpf_load_percent"], (450.0, 700.0),
        "⚠️ LEGAL: afeta sistema de pós-tratamento de emissões."),
    MapDefinition("scr_urea_dosing", MapCategory.EMISSION,
        "Dosagem de ureia AdBlue (mg/ciclo)",
        "mg/ciclo", ["exhaust_temp", "nox_ppm"], (0.0, 50.0),
        "⚠️ LEGAL: SCR/AdBlue afeta emissões de NOx — restrições legais severas."),
    # Imobilizador — Guardian 4
    MapDefinition("immobilizer_code_table", MapCategory.IMMOBILIZER,
        "Tabela de códigos do imobilizador",
        "hex", [], (0x0, 0xFFFF),
        "⚠️ LEGAL: alteração pode configurar crime. Apenas com autorização documentada."),
    # Odômetro — Guardian 4
    MapDefinition("odometer_value", MapCategory.ODOMETER,
        "Valor do odômetro",
        "km", [], (0.0, 999999.0),
        "⚠️ LEGAL: alteração de odômetro é crime em todos os países. Permitido apenas para recuperação após falha documentada."),
]

_MAP_INDEX: dict[str, MapDefinition] = {m.name: m for m in _KNOWN_MAPS}


def get_map(name: str) -> Optional[MapDefinition]:
    return _MAP_INDEX.get(name)


def list_maps(category: Optional[MapCategory] = None) -> list[MapDefinition]:
    if category is None:
        return list(_KNOWN_MAPS)
    return [m for m in _KNOWN_MAPS if m.category == category]


def guardian_level_for_map(map_name: str) -> int:
    m = _MAP_INDEX.get(map_name)
    return m.guardian_level if m else 2
