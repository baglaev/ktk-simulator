from enum import Enum


class UserRole(str, Enum):
    TRAINEE = "trainee"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class TrainingMode(str, Enum):
    TRAINING = "training"
    CONTROL = "control"


class SessionStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EquipmentType(str, Enum):
    PUMP_GROUP = "pump_group"
    TANK = "tank"
    PUMP = "pump"
    PIPELINE = "pipeline"
    HEAT_EXCHANGER = "heat_exchanger"
    DESALTER = "desalter"
    VESSEL = "vessel"
    COLUMN = "column"
    FURNACE = "furnace"
    SENSOR = "sensor"


class EquipmentStatus(str, Enum):
    AVAILABLE = "available"
    RUNNING = "running"
    STOPPED = "stopped"
    FAULT = "fault"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class MeasurementType(str, Enum):
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    FLOW_RATE = "flow_rate"
    LEVEL = "level"
    VIBRATION_VELOCITY = "vibration_velocity"
    VIBRATION_ACCELERATION = "vibration_acceleration"
    VIBRATION_DISPLACEMENT = "vibration_displacement"
    ELECTRIC_CURRENT = "electric_current"
    POWER = "power"
    POSITION = "position"
    STATE = "state"


class GeneralStatus(str, Enum):
    """Common traffic-light status used by every frontend component."""

    SUCCESS = "success"
    WARNING = "warning"
    ALERT = "alert"


class ParameterOrigin(str, Enum):
    SOURCE = "source"
    TEAM = "team"
    EDUCATIONAL_ASSUMPTION = "educational_assumption"


class ActionType(str, Enum):
    OPEN_EQUIPMENT_CARD = "open_equipment_card"
    VIEW_SIGNAL = "view_signal"
    RUN_DIAGNOSTICS = "run_diagnostics"
    SUBMIT_DECISION = "submit_decision"
    ACKNOWLEDGE_EVENT = "acknowledge_event"


class EventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
