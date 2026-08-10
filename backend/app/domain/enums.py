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
    READY_TO_COMPLETE = "ready_to_complete"
    COMPLETED = "completed"
    FAILED = "failed"
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
    SUBMIT_DIAGNOSIS = "submit_diagnosis"
    START_PUMP = "start_pump"
    STOP_PUMP = "stop_pump"


class DiagnosisConclusion(str, Enum):
    FAULT_DETECTED = "fault_detected"
    NO_FAULT = "no_fault"


class DiagnosisReason(str, Enum):
    BEARING_WEAR = "bearing_wear"
    CAVITATION = "cavitation"
    ELECTRICAL_OVERLOAD = "electrical_overload"
    UNKNOWN = "unknown"


class ScenarioOutcome(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


class ActionErrorCode(str, Enum):
    SWITCH_BEFORE_DIAGNOSIS = "switch_before_diagnosis"
    HEALTHY_PUMP_SELECTED = "healthy_pump_selected"
    FAULT_NOT_DETECTED = "fault_not_detected"
    WRONG_DIAGNOSIS_REASON = "wrong_diagnosis_reason"
    DIAGNOSIS_TOO_LATE = "diagnosis_too_late"
    DIAGNOSIS_WITHOUT_PRA_CHECK = "diagnosis_without_pra_check"
    DIAGNOSIS_WITHOUT_FYQR_CHECK = "diagnosis_without_fyqr_check"
    WRONG_DIAGNOSIS_CORRECTED = "wrong_diagnosis_corrected"
    PUMP_COMMAND_BEFORE_WARNING = "pump_command_before_warning"
    N1A_STOPPED_BEFORE_N1B = "n1a_stopped_before_n1b"
    N1A_STOPPED_WITHOUT_DIAGNOSIS = "n1a_stopped_without_diagnosis"
    HEALTHY_PUMP_STOPPED = "healthy_pump_stopped"
    N1A_LEFT_RUNNING = "n1a_left_running"
    N1B_STOPPED_AFTER_START = "n1b_stopped_after_start"
    N1A_RESTARTED_AFTER_SWITCH = "n1a_restarted_after_switch"
    MULTIPLE_PUMPS_STOPPED = "multiple_pumps_stopped"
    UNNECESSARY_REPEATED_SWITCHING = "unnecessary_repeated_switching"
    WARNING_IGNORED = "warning_ignored"
    PRA_NOT_CHECKED = "pra_not_checked"
    FYQR_NOT_CHECKED = "fyqr_not_checked"
    ELOU_NOT_CHECKED_AFTER_SWITCH = "elou_not_checked_after_switch"
    E15_NOT_CHECKED_AFTER_SWITCH = "e15_not_checked_after_switch"
    LRCA_RECOVERY_NOT_CONFIRMED = "lrca_recovery_not_confirmed"
    COMPLETED_BEFORE_STABLE = "completed_before_stable"
    E15_SAFETY_LIMIT_REACHED = "e15_safety_limit_reached"


class EventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
