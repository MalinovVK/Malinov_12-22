import json
import logging
import random
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional

# Настройка логирования с перезаписью файла
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('rza_simulation.log', mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('RZA_Substation')


# Перечисления для типов повреждений и состояний
class FaultType(Enum):
    THREE_PHASE = "трехфазное КЗ"
    SINGLE_PHASE = "однофазное КЗ"
    TWO_PHASE = "двухфазное КЗ"
    WINDING = "витковое замыкание"


class ProtectionType(Enum):
    MAIN = "основная защита"
    RESERVE = "резервная защита"


class EquipmentStatus(Enum):
    NORMAL = "нормальный режим"
    FAULT = "авария"
    TRIPPED = "отключено"


# Базовый класс для всего оборудования (наследование)
class Equipment:
    """Базовый класс для всего первичного оборудования"""

    def __init__(self, name: str, voltage: int):
        self.name = name
        self.voltage = voltage
        self.status = EquipmentStatus.NORMAL
        self.breaker: Optional['Breaker'] = None  # Агрегация - один выключатель на оборудование


    def get_status(self) -> str:
        return f"{self.name}: {self.status.value}"

    def trip(self):
        """Отключение оборудования"""
        self.status = EquipmentStatus.TRIPPED
        # Отключаем связанный выключатель
        if self.breaker:
            self.breaker.open()
            logger.info(f"Оборудование {self.name} ОТКЛЮЧЕНО выключателем {self.breaker.name}")
        else:
            logger.warning(f"Оборудование {self.name} не имеет выключателя!")

    def set_breaker(self, breaker: 'Breaker'):
        """Установка выключателя для оборудования"""
        self.breaker = breaker
        logger.info(f"Оборудование {self.name} связано с выключателем {breaker.name}")

    def get_fault_current(self, fault_type: FaultType) -> float:
        """Получение тока КЗ для оборудования"""
        # Базовый метод - должен быть переопределен в дочерних классах
        return random.uniform(5.0, 20.0)


# Классы первичного оборудования (наследование от Equipment)
class Bus(Equipment):
    """Класс для систем шин"""

    def __init__(self, name: str, voltage: int):
        super().__init__(name, voltage)
        self.connected_equipment: List[Equipment] = []  # Агрегация
        # Ток КЗ на шинах зависит от напряжения
        self.base_fault_current = {
            220: random.uniform(3.0, 10.0),
            110: random.uniform(4.5, 15.0),
            10: random.uniform(20.0, 100.0)
        }.get(voltage, random.uniform(5.0, 20.0))

    def add_equipment(self, equipment: Equipment):
        self.connected_equipment.append(equipment)
        logger.info(f"Шина {self.name}: подключено оборудование {equipment.name}")

    def get_fault_current(self, fault_type: FaultType) -> float:
        """Ток КЗ на шинах"""
        if fault_type == FaultType.THREE_PHASE:
            return self.base_fault_current * 1.2
        elif fault_type == FaultType.TWO_PHASE:
            return self.base_fault_current * 0.87
        elif fault_type == FaultType.SINGLE_PHASE:
            return self.base_fault_current * 1.1
        else:  # WINDING не применим к шинам
            return self.base_fault_current


class Breaker(Equipment):
    """Класс для выключателей"""

    def __init__(self, name: str, voltage: int):
        super().__init__(name, voltage)
        self.is_closed = True

    def open(self):
        self.is_closed = False
        logger.info(f"Выключатель {self.name} РАЗОМКНУТ")

    def close(self):
        self.is_closed = True
        logger.info(f"Выключатель {self.name} ЗАМКНУТ")

    def get_fault_current(self, fault_type: FaultType) -> float:
        """Ток КЗ через выключатель"""
        return 0.0


class Transformer(Equipment):
    """Класс для трехфазных трансформаторов 220/110/10"""

    def __init__(self, name: str, power: int):
        super().__init__(name, 220)  # Номинальное напряжение высшей стороны
        self.power = power  # МВА
        self.hv = 220  # кВ - высшая сторона
        self.mv = 110  # кВ - средняя сторона
        self.lv = 10  # кВ - низшая сторона
        self.winding_status = EquipmentStatus.NORMAL

        # Токи КЗ для разных сторон (в кА)
        self.fault_currents = {
            "hv": random.uniform(4.0, 9.0),  # ток КЗ на высокой стороне
            "mv": random.uniform(5.0, 13.0),  # ток КЗ на средней стороне
            "lv": random.uniform(20.0, 73.0)  # ток КЗ на низкой стороне
        }

    def get_fault_current(self, fault_type: FaultType) -> float:
        """Ток КЗ в трансформаторе"""
        # Для витковых замыканий ток может быть меньше
        if fault_type == FaultType.WINDING:
            return random.uniform(2.0, 6.0)

        # Выбираем случайную сторону для КЗ
        side = random.choice(["hv", "mv", "lv"])
        base_current = self.fault_currents[side]

        if fault_type == FaultType.THREE_PHASE:
            return base_current
        elif fault_type == FaultType.TWO_PHASE:
            return base_current * 0.87
        else:  # SINGLE_PHASE
            return base_current * 1.1


class Line(Equipment):
    """Класс для линий электропередачи"""

    def __init__(self, name: str, voltage: int, length: float):
        super().__init__(name, voltage)
        self.length = length  # км
        # Ток КЗ для линии зависит от длины и напряжения
        self.base_fault_current = random.uniform(3.0, 15.0) * (1 - length / 200)  # Чем длиннее, тем меньше ток

    def get_fault_current(self, fault_type: FaultType) -> float:
        """Ток КЗ на линии"""
        if fault_type == FaultType.THREE_PHASE:
            return self.base_fault_current
        elif fault_type == FaultType.TWO_PHASE:
            return self.base_fault_current * 0.87
        elif fault_type == FaultType.SINGLE_PHASE:
            return self.base_fault_current * 1.15
        else:  # WINDING не применим к линиям
            return self.base_fault_current


# Классы для РЗА
class ProtectionRelay:
    """Базовый класс для релейной защиты"""

    def __init__(self, name: str, prot_type: ProtectionType, time_delay: float,
                 current_setting: float, failure_rate: float, voltage_level: str = "all",
                 protected_equipment_types: List[str] = None):
        self.name = name
        self.prot_type = prot_type
        self.time_delay = time_delay
        self.current_setting = current_setting  # уставка по току
        self.failure_rate = failure_rate  # вероятность отказа (0-1)
        self.voltage_level = voltage_level  # для какой стороны: "hv", "mv", "lv", "all"
        self.protected_equipment_types = protected_equipment_types or ["transformer", "line", "bus"]
        self.is_triggered = False
        self.has_failed = False  # отказала ли защита
        self.protected_equipment_name: Optional[str] = None  # конкретное оборудование, которое защищает
        self.last_check_logged = False  # для предотвращения дублирования логов
        logger.info(f"Создана {prot_type.value}: {name} (Iуст={current_setting}, Pотказа={failure_rate})")

    def set_protected_equipment(self, equipment_name: str):
        """Установка конкретного оборудования для защиты"""
        self.protected_equipment_name = equipment_name

    def should_protect(self, equipment: Equipment) -> bool:
        """Проверяет, должна ли данная защита реагировать на это оборудование"""
        # Если указано конкретное оборудование, проверяем по имени
        if self.protected_equipment_name:
            return equipment.name == self.protected_equipment_name

        # Иначе проверяем по типу и напряжению
        equipment_type = equipment.__class__.__name__.lower()

        # Проверка соответствия типу оборудования
        type_match = False
        for protected_type in self.protected_equipment_types:
            if protected_type in equipment_type:
                type_match = True
                break

        if not type_match:
            return False

        # Проверка по напряжению
        if self.voltage_level == "hv" and equipment.voltage == 220:
            return True
        elif self.voltage_level == "mv" and equipment.voltage == 110:
            return True
        elif self.voltage_level == "lv" and equipment.voltage == 10:
            return True
        elif self.voltage_level == "all":
            return True

        return False

    def check_fault(self, fault_type: FaultType, equipment: Equipment, fault_current: float) -> bool:
        """Проверка условий срабатывания защиты"""
        # Проверка, должна ли защита реагировать на это оборудование
        if not self.should_protect(equipment):
            self.last_check_logged = False
            return False

        # Проверка отказа защиты
        if random.random() < self.failure_rate:
            if not self.has_failed:
                self.has_failed = True
                logger.warning(f"ЗАЩИТА {self.name} ОТКАЗАЛА!")
            self.last_check_logged = False
            return False

        # Проверка превышения тока уставки
        if fault_current > self.current_setting:
            # Логируем только один раз за все время проверки
            if not self.last_check_logged:
                logger.info(f"Защита {self.name}: ток {fault_current:.2f} > уставки {self.current_setting}")
                self.last_check_logged = True
            return True
        else:
            if not self.last_check_logged:
                logger.info(f"Защита {self.name}: ток {fault_current:.2f} <= уставки {self.current_setting}")
                self.last_check_logged = True
            return False

    def trigger(self, equipment: Equipment, current_time: float):
        """Срабатывание защиты"""
        if not self.is_triggered and not self.has_failed:
            logger.warning(f"ВРЕМЯ {current_time:.3f}с: {self.prot_type.value} {self.name} СРАБОТАЛА")
            self.is_triggered = True
            equipment.trip()
            return True
        return False

    def reset_log_flag(self):
        """Сброс флага логирования для новой итерации"""
        self.last_check_logged = False


class DifferentialProtection(ProtectionRelay):
    """Дифференциальная защита (для трансформаторов)"""

    def __init__(self, name: str, prot_type: ProtectionType, time_delay: float,
                 current_setting: float, failure_rate: float, voltage_level: str = "all"):
        super().__init__(name, prot_type, time_delay, current_setting, failure_rate,
                         voltage_level, ["transformer"])

    def check_fault(self, fault_type: FaultType, equipment: Equipment, fault_current: float) -> bool:
        # Дифзащита всегда срабатывает при витковых замыканиях
        if isinstance(equipment, Transformer) and fault_type == FaultType.WINDING:
            if random.random() < self.failure_rate:
                if not self.has_failed:
                    self.has_failed = True
                    logger.warning(f"ЗАЩИТА {self.name} ОТКАЗАЛА!")
                self.last_check_logged = False
                return False

            if not self.last_check_logged:
                logger.info(f"Дифференциальная защита обнаружила витковое замыкание")
                self.last_check_logged = True
            return True

        # Для остальных случаев используем базовую логику
        return super().check_fault(fault_type, equipment, fault_current)


class OvercurrentProtection(ProtectionRelay):
    """Максимальная токовая защита"""

    def __init__(self, name: str, prot_type: ProtectionType, time_delay: float,
                 current_setting: float, failure_rate: float, voltage_level: str = "all"):
        super().__init__(name, prot_type, time_delay, current_setting, failure_rate,
                         voltage_level, ["transformer", "line", "bus"])

    def check_fault(self, fault_type: FaultType, equipment: Equipment, fault_current: float) -> bool:
        # МТЗ не реагирует на витковые замыкания в трансформаторах
        if isinstance(equipment, Transformer) and fault_type == FaultType.WINDING:
            self.last_check_logged = False
            return False

        return super().check_fault(fault_type, equipment, fault_current)


class LineProtection(ProtectionRelay):
    """Защита линий"""

    def __init__(self, name: str, prot_type: ProtectionType, time_delay: float,
                 current_setting: float, failure_rate: float, voltage_level: str = "all"):
        super().__init__(name, prot_type, time_delay, current_setting, failure_rate,
                         voltage_level, ["line"])


# Класс подстанции (композиция)
# Класс подстанции (композиция)
class Substation:
    """Класс понижающей подстанции с двумя трансформаторами 220/110/10"""

    def __init__(self, name: str, config_file: str, protections_config: str):
        self.name = name
        self.time = 0.0
        self.equipment: Dict[str, Equipment] = {}  # Агрегация
        self.protections: List[ProtectionRelay] = []  # Агрегация
        self.buses: Dict[str, Bus] = {}  # Агрегация
        self.fault_active = False
        self.current_fault = None
        self.fault_equipment = None
        self.fault_current = 0.0
        self.fault_start_time = 0.0
        self.trip_time = None
        self._reserve_check_logged = False  # Флаг для логирования резервных защит

        logger.info(f"Создание подстанции {name}")
        self.load_configuration(config_file)
        self.load_protections_config(protections_config)
        self.setup_breaker_connections()

    def load_configuration(self, config_file: str):
        """Загрузка конфигурации из JSON файла"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Создание шин
            for bus_data in config.get('buses', []):
                bus = Bus(bus_data['name'], bus_data['voltage'])
                self.buses[bus.name] = bus
                self.equipment[bus.name] = bus

            # Создание выключателей
            for breaker_data in config.get('breakers', []):
                breaker = Breaker(breaker_data['name'], breaker_data['voltage'])
                self.equipment[breaker.name] = breaker
                # Подключение к шине
                if breaker_data.get('bus') in self.buses:
                    self.buses[breaker_data['bus']].add_equipment(breaker)

            # Создание двух трехфазных трансформаторов 220/110/10
            for trans_data in config.get('transformers', []):
                transformer = Transformer(
                    trans_data['name'],
                    trans_data['power']
                )
                self.equipment[transformer.name] = transformer

            # Создание линий
            for line_data in config.get('lines', []):
                line = Line(line_data['name'], line_data['voltage'], line_data['length'])
                self.equipment[line.name] = line

            logger.info(f"Загружена конфигурация: {len(self.equipment)} единиц оборудования")

        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")

    def load_protections_config(self, config_file: str):
        """Загрузка конфигурации защит из JSON файла"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Создание защит согласно конфигурации
            for prot_data in config.get('protections', []):
                if prot_data['type'] == 'differential':
                    protection = DifferentialProtection(
                        prot_data['name'],
                        ProtectionType.MAIN if prot_data['main'] else ProtectionType.RESERVE,
                        prot_data['time_delay'],
                        prot_data['current_setting'],
                        prot_data['failure_rate'],
                        prot_data.get('voltage_level', 'all')
                    )
                elif prot_data['type'] == 'line':
                    protection = LineProtection(
                        prot_data['name'],
                        ProtectionType.MAIN if prot_data['main'] else ProtectionType.RESERVE,
                        prot_data['time_delay'],
                        prot_data['current_setting'],
                        prot_data['failure_rate'],
                        prot_data.get('voltage_level', 'all')
                    )
                else:  # overcurrent
                    protection = OvercurrentProtection(
                        prot_data['name'],
                        ProtectionType.MAIN if prot_data['main'] else ProtectionType.RESERVE,
                        prot_data['time_delay'],
                        prot_data['current_setting'],
                        prot_data['failure_rate'],
                        prot_data.get('voltage_level', 'all')
                    )

                # Если в конфиге указано конкретное оборудование для защиты
                if 'protects' in prot_data:
                    protection.set_protected_equipment(prot_data['protects'])

                self.protections.append(protection)

            logger.info(f"Загружено {len(self.protections)} защит из конфигурации")

        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации защит: {e}")

    def setup_breaker_connections(self):
        """Настройка связей между оборудованием и выключателями (один к одному)"""
        # Словарь соответствия: имя оборудования -> имя выключателя
        breaker_mapping = {
            # Линии 220 кВ
            "Л1-220": "Q1-220",
            "Л2-220": "Q2-220",
            # Линии 110 кВ
            "Л1-110": "Q1-110",
            "Л2-110": "Q2-110",
            # Линии 10 кВ
            "Л1-10": "Q1-10",
            "Л2-10": "Q2-10",
            # Трансформаторы
            "Т1": "Q1-220",  # Трансформатор Т1 связан с выключателем Q1-220
            "Т2": "Q2-220",  # Трансформатор Т2 связан с выключателем Q2-220
            # Шины
            "Ш1-220": "Q1-220",
            "Ш2-220": "Q2-220",
            "ОШ-220": "QO-220",
            "РШ-110-1": "Q1-110",
            "РШ-110-2": "Q2-110",
            "ОШ-110": "QO-110",
            "СШ-10-1": "Q1-10",
            "СШ-10-2": "Q2-10"
        }

        # Устанавливаем связи
        for eq_name, breaker_name in breaker_mapping.items():
            if eq_name in self.equipment and breaker_name in self.equipment:
                equipment = self.equipment[eq_name]
                breaker = self.equipment[breaker_name]
                equipment.set_breaker(breaker)


    def apply_fault(self, equipment_name: str, fault_type: FaultType):
        """Применение повреждения к оборудованию"""
        if equipment_name in self.equipment:
            equipment = self.equipment[equipment_name]

            # Не применяем КЗ к выключателям
            if isinstance(equipment, Breaker):
                logger.warning(f"КЗ на выключателе {equipment_name} не моделируется")
                return False

            equipment.status = EquipmentStatus.FAULT
            self.fault_active = True
            self.current_fault = fault_type
            self.fault_equipment = equipment
            self.fault_start_time = self.time

            # Получаем ток КЗ для данного оборудования
            self.fault_current = equipment.get_fault_current(fault_type)

            logger.info(f"ПОВРЕЖДЕНИЕ: {fault_type.value} на {equipment_name}!")
            return True
        return False

    def check_protections(self) -> List[str]:
        """Проверка срабатывания защит с учетом селективности и резервирования"""
        tripped_equipment = []

        if not self.fault_active:
            return tripped_equipment

        # Находим все защиты, которые могут сработать на этом оборудовании
        relevant_protections = []
        for protection in self.protections:
            if protection.should_protect(self.fault_equipment):
                relevant_protections.append(protection)

        # Разделяем на основные и резервные защиты
        main_protections = [p for p in relevant_protections if p.prot_type == ProtectionType.MAIN]
        reserve_protections = [p for p in relevant_protections if p.prot_type == ProtectionType.RESERVE]

        # Сортируем защиты по времени срабатывания
        main_protections.sort(key=lambda p: p.time_delay)
        reserve_protections.sort(key=lambda p: p.time_delay)

        # Проверяем основные защиты
        main_triggered = False
        for protection in main_protections:
            if not protection.is_triggered and not protection.has_failed:
                if protection.check_fault(self.current_fault, self.fault_equipment, self.fault_current):
                    time_from_fault = self.time - self.fault_start_time
                    if time_from_fault >= protection.time_delay:
                        if protection.trigger(self.fault_equipment, self.time):
                            tripped_equipment.append(self.fault_equipment.name)
                            self.fault_active = False
                            self.trip_time = self.time
                            logger.info(f"Сработала основная защита {protection.name}")
                            main_triggered = True
                            break

        # Если основные не сработали (отказ или нет реакции), проверяем резервные
        if not main_triggered and self.fault_active:
            # Проверяем, нужно ли логировать сообщение (только один раз)
            if not self._reserve_check_logged:
                logger.info("Основные защиты не сработали - проверка резервных защит")
                self._reserve_check_logged = True

            for protection in reserve_protections:
                if not protection.is_triggered and not protection.has_failed:
                    if protection.check_fault(self.current_fault, self.fault_equipment, self.fault_current):
                        time_from_fault = self.time - self.fault_start_time
                        if time_from_fault >= protection.time_delay:
                            if protection.trigger(self.fault_equipment, self.time):
                                tripped_equipment.append(self.fault_equipment.name)
                                self.fault_active = False
                                self.trip_time = self.time
                                logger.info(f"Сработала резервная защита {protection.name}")
                                break

        return tripped_equipment

    def step(self, delta_time: float = 0.1):
        """Шаг симуляции"""
        self.time += delta_time
        tripped = self.check_protections()

        if tripped:
            logger.info(f"Время {self.time:.1f}с")

        return tripped

    def reset_protection_logs(self):
        """Сброс флагов логирования защит"""
        for protection in self.protections:
            protection.reset_log_flag()
        # Сброс флага проверки резервных защит
        self._reserve_check_logged = False


def create_default_configs():
    """Создание конфигурационных файлов"""

    # Конфигурация оборудования
    equipment_config = {
        "buses": [
            # Высшая сторона 220 кВ
            {"name": "Ш1-220", "voltage": 220},
            {"name": "Ш2-220", "voltage": 220},
            {"name": "ОШ-220", "voltage": 220},
            # Средняя сторона 110 кВ
            {"name": "РШ-110-1", "voltage": 110},
            {"name": "РШ-110-2", "voltage": 110},
            {"name": "ОШ-110", "voltage": 110},
            # Низшая сторона 10 кВ
            {"name": "СШ-10-1", "voltage": 10},
            {"name": "СШ-10-2", "voltage": 10}
        ],
        "breakers": [
            # Выключатели 220 кВ
            {"name": "Q1-220", "voltage": 220, "bus": "Ш1-220"},
            {"name": "Q2-220", "voltage": 220, "bus": "Ш2-220"},
            {"name": "QO-220", "voltage": 220, "bus": "ОШ-220"},
            # Выключатели 110 кВ
            {"name": "Q1-110", "voltage": 110, "bus": "РШ-110-1"},
            {"name": "Q2-110", "voltage": 110, "bus": "РШ-110-2"},
            {"name": "QO-110", "voltage": 110, "bus": "ОШ-110"},
            # Выключатели 10 кВ
            {"name": "Q1-10", "voltage": 10, "bus": "СШ-10-1"},
            {"name": "Q2-10", "voltage": 10, "bus": "СШ-10-2"}
        ],
        "transformers": [
            {"name": "Т1", "power": 200},
            {"name": "Т2", "power": 200}
        ],
        "lines": [
            # Линии 220 кВ
            {"name": "Л1-220", "voltage": 220, "length": 50},
            {"name": "Л2-220", "voltage": 220, "length": 75},
            # Линии 110 кВ
            {"name": "Л1-110", "voltage": 110, "length": 30},
            {"name": "Л2-110", "voltage": 110, "length": 45},
            # Линии 10 кВ
            {"name": "Л1-10", "voltage": 10, "length": 5},
            {"name": "Л2-10", "voltage": 10, "length": 8}
        ]
    }

    # Конфигурация защит - добавлены резервные защиты
    protections_config = {
        "protections": [
            # Дифференциальные защиты линий 220 кВ (ДЗЛ) - ОСНОВНЫЕ
            {
                "name": "ДЗЛ-220-1",
                "type": "line",
                "main": True,
                "time_delay": 0.2,
                "current_setting": 8.0,
                "failure_rate": 0.03,
                "voltage_level": "hv",
                "protects": "Л1-220"
            },
            {
                "name": "ДЗЛ-220-2",
                "type": "line",
                "main": True,
                "time_delay": 0.2,
                "current_setting": 8.0,
                "failure_rate": 0.03,
                "voltage_level": "hv",
                "protects": "Л2-220"
            },
            # Дифференциальные защиты линий 110 кВ (ДЗЛ) - ОСНОВНЫЕ
            {
                "name": "ДЗЛ-110-1",
                "type": "line",
                "main": True,
                "time_delay": 0.2,
                "current_setting": 6.0,
                "failure_rate": 0.03,
                "voltage_level": "mv",
                "protects": "Л1-110"
            },
            {
                "name": "ДЗЛ-110-2",
                "type": "line",
                "main": True,
                "time_delay": 0.2,
                "current_setting": 6.0,
                "failure_rate": 0.03,
                "voltage_level": "mv",
                "protects": "Л2-110"
            },
            # Дифференциальные защиты линий 10 кВ (ДЗЛ) - ОСНОВНЫЕ
            {
                "name": "ДЗЛ-10-1",
                "type": "overcurrent",
                "main": True,
                "time_delay": 0.2,
                "current_setting": 5.0,
                "failure_rate": 0.03,
                "voltage_level": "lv",
                "protects": "Л1-10"
            },
            {
                "name": "ДЗЛ-10-2",
                "type": "overcurrent",
                "main": True,
                "time_delay": 0.2,
                "current_setting": 5.0,
                "failure_rate": 0.03,
                "voltage_level": "lv",
                "protects": "Л2-10"
            },
            # Дифференциальные защиты трансформаторов - ОСНОВНЫЕ
            {
                "name": "ДЗТ-Т1",
                "type": "differential",
                "main": True,
                "time_delay": 0.1,
                "current_setting": 0.5,
                "failure_rate": 0.05,
                "voltage_level": "all",
                "protects": "Т1"
            },
            {
                "name": "ДЗТ-Т2",
                "type": "differential",
                "main": True,
                "time_delay": 0.1,
                "current_setting": 0.5,
                "failure_rate": 0.05,
                "voltage_level": "all",
                "protects": "Т2"
            },
            # Дифференциальные защиты шин (основные)
            {
                "name": "ДЗШ-220-1",
                "type": "overcurrent",
                "main": True,
                "time_delay": 0.3,
                "current_setting": 12.0,
                "failure_rate": 0.04,
                "voltage_level": "hv",
                "protects": "Ш1-220"
            },
            {
                "name": "ДЗШ-220-2",
                "type": "overcurrent",
                "main": True,
                "time_delay": 0.3,
                "current_setting": 12.0,
                "failure_rate": 0.04,
                "voltage_level": "hv",
                "protects": "Ш2-220"
            },
            # РЕЗЕРВНЫЕ ЗАЩИТЫ
            {
                "name": "МТЗ-220-1",
                "type": "overcurrent",
                "main": False,
                "time_delay": 0.8,
                "current_setting": 7.0,
                "failure_rate": 0.02,
                "voltage_level": "hv",
                "protects": "Л1-220"
            },
            {
                "name": "МТЗ-220-2",
                "type": "overcurrent",
                "main": False,
                "time_delay": 0.8,
                "current_setting": 7.0,
                "failure_rate": 0.02,
                "voltage_level": "hv",
                "protects": "Л2-220"
            },
            {
                "name": "МТЗ-110-1",
                "type": "overcurrent",
                "main": False,
                "time_delay": 0.8,
                "current_setting": 5.0,
                "failure_rate": 0.02,
                "voltage_level": "mv",
                "protects": "Л1-110"
            },
            {
                "name": "МТЗ-110-2",
                "type": "overcurrent",
                "main": False,
                "time_delay": 0.8,
                "current_setting": 5.0,
                "failure_rate": 0.02,
                "voltage_level": "mv",
                "protects": "Л2-110"
            },
            {
                "name": "МТЗ-10-1",
                "type": "overcurrent",
                "main": False,
                "time_delay": 0.8,
                "current_setting": 4.0,
                "failure_rate": 0.02,
                "voltage_level": "lv",
                "protects": "Л1-10"
            },
            {
                "name": "МТЗ-10-2",
                "type": "overcurrent",
                "main": False,
                "time_delay": 0.8,
                "current_setting": 4.0,
                "failure_rate": 0.02,
                "voltage_level": "lv",
                "protects": "Л2-10"
            },
            {
                "name": "МТЗ-Т1",
                "type": "overcurrent",
                "main": False,
                "time_delay": 0.6,
                "current_setting": 7.0,
                "failure_rate": 0.02,
                "voltage_level": "hv",
                "protects": "Т1"
            },
            {
                "name": "МТЗ-Т2",
                "type": "overcurrent",
                "main": False,
                "time_delay": 0.6,
                "current_setting": 7.0,
                "failure_rate": 0.02,
                "voltage_level": "hv",
                "protects": "Т2"
            }
        ]
    }

    with open('substation_config.json', 'w', encoding='utf-8') as f:
        json.dump(equipment_config, f, indent=2, ensure_ascii=False)

    with open('protections_config.json', 'w', encoding='utf-8') as f:
        json.dump(protections_config, f, indent=2, ensure_ascii=False)


def main():
    """Основная функция симуляции"""

    import os

    # Имена файлов конфигурации
    substation_config_file = 'substation_config.json'
    protections_config_file = 'protections_config.json'

    # ПРОВЕРЯЕМ существование файлов конфигурации
    if not (os.path.exists(substation_config_file) and os.path.exists(protections_config_file)):
        # Если файлов нет - создаем их
        logger.warning("Файлы конфигурации не найдены! Создаю новые...")
        create_default_configs()
    else:
        # ЕСЛИ ФАЙЛЫ СУЩЕСТВУЮТ - просто сообщаем об этом
        logger.info("Использую существующие файлы конфигурации:")
        logger.info(f"  - {substation_config_file}")
        logger.info(f"  - {protections_config_file}")

    # Создание подстанции - ВСЕГДА читает из файлов
    logger.info("\nЗагрузка подстанции из файлов конфигурации...")
    substation = Substation("ПС-220/110/10", substation_config_file, protections_config_file)

    # Выводим информацию о загруженном оборудовании
    transformers = [eq for eq in substation.equipment.values() if isinstance(eq, Transformer)]
    lines = [eq for eq in substation.equipment.values() if isinstance(eq, Line)]
    buses = [eq for eq in substation.equipment.values() if isinstance(eq, Bus)]
    breakers = [eq for eq in substation.equipment.values() if isinstance(eq, Breaker)]


    # Список оборудования для тестирования (исключаем выключатели)
    equipment_list = [name for name, eq in substation.equipment.items()
                      if not isinstance(eq, Breaker)]
    fault_types = list(FaultType)

    # Симуляция 15 итераций
    iteration = 0
    max_iterations = 15



    while iteration < max_iterations:
        iteration += 1
        logger.info(f"\n--- Итерация {iteration} ---")

        # Сброс состояния
        substation.time = 0
        substation.fault_active = False
        substation.fault_start_time = 0
        substation.trip_time = None
        substation._reserve_check_logged = False
        for prot in substation.protections:
            prot.is_triggered = False
            prot.has_failed = False
        substation.reset_protection_logs()
        for eq in substation.equipment.values():
            eq.status = EquipmentStatus.NORMAL

        # Выбор случайного оборудования и типа повреждения
        test_equipment = random.choice(equipment_list)
        test_fault = random.choice(fault_types)

        # Применение повреждения
        substation.apply_fault(test_equipment, test_fault)

        # Цикл времени для данной итерации
        time_step = 0.1
        max_time = round(random.random() * 10, 2)



        while substation.time <= max_time and substation.fault_active:
            tripped = substation.step(time_step)

            if tripped:
                logger.info(f"Авария ликвидирована за {substation.time - substation.fault_start_time:.2f}с")
                break

        if substation.fault_active:
            logger.error(f"Защита НЕ СРАБОТАЛА за {max_time}с!")

        logger.info(f"Итерация {iteration} завершена")




if __name__ == "__main__":
    main()