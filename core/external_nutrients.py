

# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: __init__
# Source: danielfm/pybreaker
# Harvested: 2026-06-23T16:37:07.878882+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: edbe0b3d1c01
# ═══════════════════════════════════════════════════════════════
class CircuitBreakerStorageBasedTestCase:
    """Mix in to test against different storage backings. Depends on
    `self.breaker` and `self.breaker_kwargs`.
    """

    def __init__(self):
        self.breaker_kwargs = None

    def test_successful_call(self):
        """CircuitBreaker: it should keep the circuit closed after a successful
        call.
        """

        def func():
            return True

        assert self.breaker.call(func)
        assert self.breaker.fail_counter == 0
        assert self.breaker.current_state == "closed"

    def test_one_failed_call(self):
        """CircuitBreaker: it should keep the circuit closed after a few
        failures.
        """

        def func():
            raise NotImplementedError

        with pytest.raises(NotImplementedError):
            self.breaker.call(func)
        assert self.breaker.fail_counter == 1
        assert self.breaker.current_state == "closed"

    def test_one_successful_call_after_failed_call(self):
        """CircuitBreaker: it should keep the circuit closed after few mixed
        outcomes.
        """

        def suc():
            return True


# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: __init__
# Source: danielfm/pybreaker
# Harvested: 2026-06-23T16:37:07.880303+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 78d557edeca3
# ═══════════════════════════════════════════════════════════════
class CircuitBreaker:
    """More abstractly, circuit breakers exists to allow one subsystem to fail
    without destroying the entire system.

    This is done by wrapping dangerous operations (typically integration points)
    with a component that can circumvent calls when the system is not healthy.

    This pattern is described by Michael T. Nygard in his book 'Release It!'.
    """

    def __init__(
        self,
        fail_max: int = 5,
        reset_timeout: float = 60,
        success_threshold: int = 1,
        exclude: Iterable[type[ExceptionType] | Callable[[Any], bool]] | None = None,
        listeners: Sequence[CBListenerType] | None = None,
        state_storage: CircuitBreakerStorage | None = None,
        name: str | None = None,
        throw_new_error_on_trip: bool = True,
    ) -> None:
        """Create a new circuit breaker with the given parameters."""
        self._lock = threading.RLock()
        self._state_storage = state_storage or CircuitMemoryStorage(STATE_CLOSED)
        self._state = self._create_new_state(self.current_state)

        self._fail_max = fail_max
        self._reset_timeout = reset_timeout
        self._success_threshold = success_threshold

        self._excluded_exceptions = list(exclude or [])
        self._listeners = list(listeners or [])
        self._name = name

        self._throw_new_error_on_trip = throw_new_error_on_trip

    @property
    def fail_counter(self) -> int:
        """Return the current number of consecutive failures."""
        return self._state_storage.counter


# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: __init__
# Source: fabfuel/circuitbreaker
# Harvested: 2026-06-23T16:37:07.881814+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 0c5d48f8aa9f
# ═══════════════════════════════════════════════════════════════
class CircuitBreaker(object):
    FAILURE_THRESHOLD = 5
    RECOVERY_TIMEOUT = 30
    EXPECTED_EXCEPTION = Exception
    FALLBACK_FUNCTION = None

    def __init__(self,
                 failure_threshold=None,
                 recovery_timeout=None,
                 expected_exception=None,
                 name=None,
                 fallback_function=None
                 ):
        """
        Construct a circuit breaker.

        :param failure_threshold: break open after this many failures
        :param recovery_timeout: close after this many seconds
        :param expected_exception: either an type of Exception, iterable of Exception types, or a predicate function.
        :param name: name for this circuitbreaker
        :param fallback_function: called when the circuit is opened

           :return: Circuitbreaker instance
           :rtype: Circuitbreaker
        """
        self._last_failure = None
        self._failure_count = 0
        self._failure_threshold = failure_threshold or self.FAILURE_THRESHOLD
        self._recovery_timeout = recovery_timeout or self.RECOVERY_TIMEOUT

        # Build the failure predicate. In order of precedence, prefer the
        # * the constructor argument
        # * the subclass attribute EXPECTED_EXCEPTION
        # * the CircuitBreaker attribute EXPECTED_EXCEPTION
        if not expected_exception:
            try:
                # Introspect our final type, then grab the  value via __dict__ to avoid python Descriptor magic
                #  in the case where it's a callable function.
                expected_exception = type(self).__dict__["EXPECTED_EXCEPTION"]
            except KeyError:


# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: unknown_nutrient
# Source: fabfuel/circuitbreaker
# Harvested: 2026-06-23T16:37:07.883217+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 52229dec9ce8
# ═══════════════════════════════════════════════════════════════
    name='circuitbreaker',
    version=VERSION,
    url='https://github.com/fabfuel/circuitbreaker',
    download_url='https://github.com/fabfuel/circuitbreaker/archive/%s.tar.gz' % VERSION,
    license='BSD-3-Clause',
    author='Fabian Fuelling',
    author_email='pypi@fabfuel.de',
    description='Python Circuit Breaker pattern implementation',
    long_description=readme(),
    py_modules=['circuitbreaker'],
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX',
        'Operating System :: MacOS',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
)



# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: clean_circuit_breaker_monitor
# Source: fabfuel/circuitbreaker
# Harvested: 2026-06-23T16:37:07.884857+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 08c8b21a0176
# ═══════════════════════════════════════════════════════════════
from circuitbreaker import CircuitBreakerMonitor


class FunctionType(str, Enum):
    sync_function = "sync-function"
    sync_generator = "sync-generator"
    async_function = "async-function"
    async_generator = "async-generator"


@pytest.fixture(autouse=True)
def clean_circuit_breaker_monitor():
    CircuitBreakerMonitor.circuit_breakers = {}


@pytest.fixture(params=FunctionType, ids=[e.value for e in FunctionType])
def function_type(request):
    return request.param


@pytest.fixture
def is_async(function_type):
    return function_type.startswith("async-")


@pytest.fixture
def is_generator(function_type):
    return function_type.endswith("-generator")


@pytest.fixture
def function_factory(function_type):
    def factory(inner_call):
        def _sync(*a, **kwa):
            return inner_call(*a, **kwa)

        def _sync_gen(*a, **kwa):
            yield inner_call(*a, **kwa)

        async def _async(*a, **kwa):


# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: circuit_success
# Source: fabfuel/circuitbreaker
# Harvested: 2026-06-23T16:37:07.886538+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 98cb2d6eaf2b
# ═══════════════════════════════════════════════════════════════
from circuitbreaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerMonitor,
    STATE_CLOSED,
    STATE_HALF_OPEN,
    STATE_OPEN,
)


@pytest.fixture
def circuit_success(function):
    return CircuitBreaker()(function)


@pytest.fixture
def circuit_failure(function, function_call_error):
    return CircuitBreaker(
        failure_threshold=1,
        name="circuit_failure",
    )(function)


@pytest.fixture
def circuit_threshold_1(function):
    return CircuitBreaker(
        failure_threshold=1,
        name="threshold_1",
    )(function)


@pytest.fixture
def circuit_threshold_2_timeout_1(function):
    return CircuitBreaker(
        failure_threshold=2,
        recovery_timeout=1,
        name="threshold_2",
    )(function)




# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: resolve_circuitbreaker_call_method
# Source: fabfuel/circuitbreaker
# Harvested: 2026-06-23T16:37:07.887877+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 7c17e938821b
# ═══════════════════════════════════════════════════════════════
from circuitbreaker import CircuitBreaker, CircuitBreakerError, circuit


@pytest.fixture
def resolve_circuitbreaker_call_method(function_type):
    def cb_call(circuit_breaker):
        mapping = {
            "sync-function": circuit_breaker.call,
            "sync-generator": circuit_breaker.call_generator,
            "async-function": circuit_breaker.call_async,
            "async-generator": circuit_breaker.call_async_generator,
        }
        return mapping[function_type]

    return cb_call


class FooError(Exception):
    def __init__(self, val=None):
        self.val = val


class BarError(Exception):
    pass


def test_circuitbreaker__str__():
    cb = CircuitBreaker(name='Foobar')
    assert str(cb) == 'Foobar'


def test_circuitbreaker_unnamed__str__():
    cb = CircuitBreaker()
    assert str(cb) == 'unnamed_CircuitBreaker'


def test_circuitbreaker_error__str__():
    cb = CircuitBreaker(name='Foobar')
    cb._last_failure = Exception()
    error = CircuitBreakerError(cb)


# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: test__otel_timeout_listener__on_timeout
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.889424+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: c0b3b9b2f2e1
# ═══════════════════════════════════════════════════════════════
    from hyx.circuitbreaker import consecutive_breaker
    from hyx.telemetry.otel import CircuitBreakerListener

    reader, meter = otel_setup
    event_manager = EventManager()
    listener = CircuitBreakerListener(meter=meter)

    breaker = consecutive_breaker(
        failure_threshold=2,
        recovery_time_secs=0.1,
        recovery_threshold=1,
        listeners=[listener],
        event_manager=event_manager,
    )

    # Trigger failures to open the breaker
    for _ in range(2):
        try:
            async with breaker:
                raise RuntimeError("fail")
        except RuntimeError:
            pass

    await event_manager.wait_for_tasks()

    # Check state transition metric
    state_metrics = get_metric_value(reader, "hyx.circuitbreaker.state_transitions")
    assert len(state_metrics) == 1
    assert state_metrics[0]["attributes"]["from_state"] == "working"
    assert state_metrics[0]["attributes"]["to_state"] == "failing"


async def test__otel_timeout_listener__on_timeout(otel_setup):
    import asyncio

    from hyx.telemetry.otel import TimeoutListener
    from hyx.timeout import timeout
    from hyx.timeout.exceptions import MaxDurationExceeded

    reader, meter = otel_setup


# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: test__prometheus_timeout_listener__on_timeout
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.891120+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: fd8abc1dea7e
# ═══════════════════════════════════════════════════════════════
    from hyx.circuitbreaker import consecutive_breaker
    from hyx.telemetry.prometheus import CircuitBreakerListener

    event_manager = EventManager()
    listener = CircuitBreakerListener(registry=registry)

    breaker = consecutive_breaker(
        failure_threshold=2,
        recovery_time_secs=0.1,
        recovery_threshold=1,
        listeners=[listener],
        event_manager=event_manager,
    )

    # Trigger failures to open the breaker
    for _ in range(2):
        try:
            async with breaker:
                raise RuntimeError("fail")
        except RuntimeError:
            pass

    await event_manager.wait_for_tasks()

    # Check state transition metric
    state_transition = get_metric_value(
        registry,
        "hyx_circuitbreaker_state_transitions",
        {"from_state": "working", "to_state": "failing"},
    )
    assert state_transition == 1


async def test__prometheus_timeout_listener__on_timeout(registry):
    import asyncio

    from hyx.telemetry.prometheus import TimeoutListener
    from hyx.timeout import timeout
    from hyx.timeout.exceptions import MaxDurationExceeded



# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: test__statsd_timeout_listener__on_timeout
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.892662+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: b6325910ee91
# ═══════════════════════════════════════════════════════════════
    from hyx.circuitbreaker import consecutive_breaker
    from hyx.telemetry.statsd import CircuitBreakerListener

    event_manager = EventManager()
    listener = CircuitBreakerListener(client=statsd_client)

    breaker = consecutive_breaker(
        failure_threshold=2,
        recovery_time_secs=0.1,
        recovery_threshold=1,
        listeners=[listener],
        event_manager=event_manager,
    )

    # Trigger failures to open the breaker
    for _ in range(2):
        try:
            async with breaker:
                raise RuntimeError("fail")
        except RuntimeError:
            pass

    await event_manager.wait_for_tasks()

    # Check state transition metric
    failing = statsd_client.get_metrics_containing("circuitbreaker")
    assert any("state.failing" in m["stat"] for m in failing)


async def test__statsd_timeout_listener__on_timeout(statsd_client):
    import asyncio

    from hyx.telemetry.statsd import TimeoutListener
    from hyx.timeout import timeout
    from hyx.timeout.exceptions import MaxDurationExceeded

    event_manager = EventManager()
    listener = TimeoutListener(client=statsd_client)

    @timeout(timeout_secs=0.01, listeners=[listener], event_manager=event_manager)


# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: __init__
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.894203+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: ce69e19740bc
# ═══════════════════════════════════════════════════════════════
from hyx.circuitbreaker import BreakerListener, consecutive_breaker
from hyx.circuitbreaker.context import BreakerContext
from hyx.circuitbreaker.exceptions import BreakerFailing
from hyx.circuitbreaker.states import BreakerState, FailingState, RecoveringState, WorkingState
from hyx.events import EventManager


class Listener(BreakerListener):
    def __init__(self) -> None:
        self.state_history: list[str] = []
        self.succeed = Mock()

    async def on_working(
        self,
        context: BreakerContext,
        current_state: BreakerState,
        next_state: WorkingState,
    ) -> None:
        self.state_history.append(next_state.NAME)

    async def on_recovering(
        self,
        context: BreakerContext,
        current_state: BreakerState,
        next_state: RecoveringState,
    ) -> None:
        self.state_history.append(next_state.NAME)

    async def on_failing(
        self,
        context: BreakerContext,
        current_state: BreakerState,
        next_state: FailingState,
    ) -> None:
        self.state_history.append(next_state.NAME)

    async def on_success(self, context: BreakerContext, state: "BreakerState") -> None:
        self.state_history.append(state.NAME)
        self.succeed()



# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: __init__
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.895606+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 26ba2413c5fb
# ═══════════════════════════════════════════════════════════════
class RetryMetricListener(RetryListener):
    def __init__(self, component: RetryManager, namespace: str, meter=None, meter_provider=None) -> None:
        if meter is None:
            meter = get_meter(__name__, __version__, meter_provider)

        self._meter = meter

        self._total_retries = meter.create_counter(name=f"{namespace}.{component.name}.retries.count", unit="retries")
        self._total_failures = meter.create_counter(name=f"{namespace}.{component.name}.retries.failures")
        self._success_after_retries = meter.create_histogram(name=f"{namespace}.{component.name}.retries.success_after")

    async def on_retry(self, retry: "RetryManager", exception: Exception, counter: "Counter", backoff: float) -> None:
        self._total_retries.add(1)

    async def on_attempts_exceeded(self, retry: "RetryManager") -> None:
        self._total_failures.add(1)

    async def on_success(self, retry: "RetryManager", counter: "Counter"):
        self._success_after_retries.record(counter.current_attempt)



# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: consecutive_breaker
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.897238+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: ec66d20f284d
# ═══════════════════════════════════════════════════════════════
from hyx.circuitbreaker.events import _BREAKER_LISTENERS, BreakerListener
from hyx.circuitbreaker.managers import ConsecutiveCircuitBreaker
from hyx.circuitbreaker.states import BreakerState
from hyx.circuitbreaker.typing import DelayT
from hyx.events import EventManager, create_manager, get_default_name
from hyx.typing import ExceptionsT, FuncT


class consecutive_breaker:
    """
    Consecutive breaker is the most basic implementation of the circuit breaker pattern.
    It counts the absolute amount of times the system has been **consecutively failed** and
    turns into the `failing` state if the threshold is exceeded.

    Then the breaker waits for the `recovery` delay and moves into the `recovering` state.
    If the action is successful, the breaker gets back to the `working` state.
    Otherwise, it goes back to the `failing` state and waits again.

    Graphically, these transitions look like this:

    ``` mermaid
    stateDiagram
        [*] --> Working: start from
        Working --> Failing: failure threshold is exceeded
        Failing --> Recovering: after the recovery delay
        Recovering --> Working: after the recovery threshold is passed
        Recovering --> Failing: at least one failing result
    ```

    **Parameters**

    * **exceptions** - Exception or list of exceptions that are considered as a failure
    * **failure_threshold** - Consecutive number of failures that turns breaker into the `failing` state
    * **recovery_time_secs** - Time in seconds we give breaker to recover from the `failing` state
    * **recovery_threshold** - Number of consecutive successes that is needed to be pass to
        turn breaker back to the `working` state
    """

    __slots__ = ("_manager",)



# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: name
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.898777+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 6d506d48f817
# ═══════════════════════════════════════════════════════════════
from hyx.circuitbreaker.typing import DelayT
from hyx.typing import ExceptionsT

if TYPE_CHECKING:
    from hyx.circuitbreaker import BreakerListener


@dataclasses.dataclass
class BreakerContext:
    breaker_name: str | None
    exceptions: ExceptionsT
    failure_threshold: int
    recovery_time_secs: DelayT
    recovery_threshold: int
    event_dispatcher: "BreakerListener"

    @property
    def name(self) -> str | None:
        return self.breaker_name



# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: on_working
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.900101+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: cca2e702aa7d
# ═══════════════════════════════════════════════════════════════
from hyx.circuitbreaker.context import BreakerContext
from hyx.circuitbreaker.managers import ConsecutiveCircuitBreaker
from hyx.events import ListenerFactoryT, ListenerRegistry

if TYPE_CHECKING:
    from hyx.circuitbreaker.states import BreakerState, FailingState, RecoveringState, WorkingState

_BREAKER_LISTENERS: ListenerRegistry["ConsecutiveCircuitBreaker", "BreakerListener"] = ListenerRegistry()


class BreakerListener:
    # TODO: add on success and on exception methods

    async def on_working(
        self,
        context: BreakerContext,
        current_state: "BreakerState",
        next_state: "WorkingState",
    ) -> None: ...

    async def on_recovering(
        self,
        context: BreakerContext,
        current_state: "BreakerState",
        next_state: "RecoveringState",
    ) -> None: ...

    async def on_failing(
        self,
        context: BreakerContext,
        current_state: "BreakerState",
        next_state: "FailingState",
    ) -> None: ...

    async def on_success(self, context: BreakerContext, state: "BreakerState") -> None: ...


def register_breaker_listener(listener: BreakerListener | ListenerFactoryT) -> None:
    """
    Register a listener that will listen to all circuit breaker components in the system


# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: unknown_nutrient
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.901981+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: a3ed4fcadc9e
# ═══════════════════════════════════════════════════════════════
    Occurs when you try to execute actions that was identified as failing by the circuit breaker
    """



# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: __init__
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.903438+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 1fd97014cb3b
# ═══════════════════════════════════════════════════════════════
from hyx.circuitbreaker.context import BreakerContext
from hyx.circuitbreaker.states import BreakerState, WorkingState
from hyx.circuitbreaker.typing import DelayT
from hyx.typing import ExceptionsT, FuncT

if TYPE_CHECKING:
    from hyx.circuitbreaker import BreakerListener


class ConsecutiveCircuitBreaker:
    """
    Watch for consecutive exceptions that exceed a given threshold
    """

    __slots__ = ("_context", "_name", "_state", "_event_dispatcher")

    def __init__(
        self,
        name: str,
        exceptions: ExceptionsT,
        failure_threshold: int,
        recovery_time_secs: DelayT,
        recovery_threshold: int,
        event_dispatcher: "BreakerListener",
    ) -> None:
        self._name = name

        self._context = BreakerContext(
            breaker_name=name,
            exceptions=exceptions,
            failure_threshold=failure_threshold,
            recovery_time_secs=recovery_time_secs,
            recovery_threshold=recovery_threshold,
            event_dispatcher=event_dispatcher,
        )

        self._state: BreakerState = WorkingState(self._context)

    @property
    def state(self) -> BreakerState:


# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: __init__
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.905742+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 86626efc03fc
# ═══════════════════════════════════════════════════════════════
from hyx.circuitbreaker.context import BreakerContext
from hyx.circuitbreaker.exceptions import BreakerFailing


class BreakerState:
    NAME: str = "base"

    __slots__ = ("_context", "_event_dispatcher")

    def __init__(self, context: BreakerContext) -> None:
        self._context = context

    @property
    def name(self) -> str:
        return self.NAME

    async def before_execution(self) -> "BreakerState":
        return self

    async def on_success(self) -> "BreakerState":
        return self

    async def on_exception(self) -> "BreakerState":
        return self


class WorkingState(BreakerState):
    """
    The breaker executes given code.

    Also known as the "closed" state
    """

    NAME = "working"

    __slots__ = ("_consecutive_exceptions",)

    def __init__(self, context: BreakerContext) -> None:
        super().__init__(context)



# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: unknown_nutrient
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.907759+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: cde3ea0430dd
# ═══════════════════════════════════════════════════════════════
from hyx.circuitbreaker.api import consecutive_breaker
from hyx.circuitbreaker.events import BreakerListener, register_breaker_listener

__all__ = ("consecutive_breaker", "BreakerListener", "register_breaker_listener")



# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: fallback
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.909703+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 2cce50eae3cb
# ═══════════════════════════════════════════════════════════════
def fallback(
    handler: FallbackT,
    *,
    name: str | None = None,
    on: ExceptionsT | None = Exception,
    if_: PredicateT | None = None,
    listeners: Sequence[FallbackListener] | None = None,
    event_manager: "EventManager | None" = None,
) -> Callable[[Callable], Callable]:
    """
    Provides a fallback on exceptions and/or specific result of the original function

    **Parameters**

    * **handler** *(Callable)* - The fallback handler
    * **on** *(None | Exception | tuple[Exception, ...])* - Fall back on the give exception(s)
    * **if_** *(None | Callable)* - Fall back if the given predicate function returns True
        on the original function result
    * **name** *(None | str)* - A component name or ID (will be passed to listeners and mention in metrics)
    * **listeners** *(None | Sequence[TimeoutListener])* - List of listeners of this concreate component state
    """
    if not on and not if_:
        raise ValueError("Either on or if_ param should be specified when using the fallback decorator")

    def _decorator(func: FuncT) -> FuncT:
        manager = create_manager(
            FallbackManager,
            listeners,
            _FALLBACK_LISTENERS,
            event_manager=event_manager,
            name=name or get_default_name(func),
            handler=handler,
            exceptions=on,
            predicate=if_,
        )

        @functools.wraps(func)
        async def _wrapper(*args: Any, **kwargs: Any) -> Any:
            return await manager(func, *args, **kwargs)



# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: on_fallback
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.911838+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 8c6419d51186
# ═══════════════════════════════════════════════════════════════
class FallbackListener:
    async def on_fallback(self, fallback: "FallbackManager", result: ResultT, *args: Any, **kwargs: Any) -> None: ...


def register_fallback_listener(listener: FallbackListener | ListenerFactoryT) -> None:
    """
    Register a listener that will listen to all fallback components in the system
    """
    global _FALLBACK_LISTENERS

    _FALLBACK_LISTENERS.register(listener)



# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: __init__
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.913503+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: a9e8b5f3c77b
# ═══════════════════════════════════════════════════════════════
class FallbackManager:
    """
    Call fallback handler on exceptions or conditions
    """

    __slots__ = (
        "_handler",
        "_exceptions",
        "_predicate",
        "_name",
        "_event_dispatcher",
    )

    def __init__(
        self,
        handler: FallbackT,
        event_dispatcher: FallbackListener,
        exceptions: ExceptionsT | None = None,
        predicate: PredicateT | None = None,
        name: str | None = None,
    ) -> None:
        self._handler = handler
        self._exceptions = exceptions
        self._predicate = predicate
        self._name = name
        self._event_dispatcher = event_dispatcher

    @property
    def name(self) -> str | None:
        return self._name

    async def __call__(self, func: FuncT, *args: Any, **kwargs: Any) -> Any:
        try:
            result = await func(*args, **kwargs)

            if self._predicate and await self._predicate(result, *args, **kwargs):
                await self._event_dispatcher.on_fallback(self, result, *args, **kwargs)
                return await self._handler(result, *args, **kwargs)

            return result


# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: __call__
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.915076+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 4cec76f67166
# ═══════════════════════════════════════════════════════════════
class FallbackT(Protocol):
    async def __call__(self, result: ResultT, *args: Any, **kwargs: Any) -> Any: ...



# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: retry
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.916432+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: a327490f69d3
# ═══════════════════════════════════════════════════════════════
def retry(
    *,
    on: ExceptionsT = Exception,
    attempts: AttemptsT = 3,
    backoff: BackoffsT = 0.5,
    name: str | None = None,
    listeners: Sequence[RetryListener] | None = None,
    event_manager: "EventManager | None" = None,
) -> Callable[[Callable], Callable]:
    """
    `@retry()` decorator retries the function `on` exceptions for the given number of `attempts`.
        Delays after each retry is defined by `backoff` strategy.

    **Parameters:**

    * **on** - Exception or tuple of Exceptions we need to retry on.
    * **attempts** - How many times do we need to retry. If `None`, it will infinitely retry until the success.
    * **backoff** - Backoff Strategy that defines delays on each retry.
        Takes `float` numbers (delay in secs), `list[floats]` (delays on each retry attempt), or `Iterator[float]`
    * **name** *(None | str)* - A component name or ID (will be passed to listeners and mention in metrics)
    * **listeners** *(None | Sequence[TimeoutListener])* - List of listeners of this concreate component state
    """

    def _decorator(func: FuncT) -> FuncT:
        manager = create_manager(
            RetryManager,
            listeners,
            _RETRY_LISTENERS,
            event_manager=event_manager,
            name=name or get_default_name(func),
            exceptions=on,
            attempts=attempts,
            backoff=backoff,
        )

        @functools.wraps(func)
        async def _wrapper(*args: Any, **kwargs: Any) -> Any:
            return await manager(cast(FuncT, functools.partial(func, *args, **kwargs)))

        _wrapper._original = func  # type: ignore[attr-defined]


# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: on_retry
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.919139+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 2aadd5e0284c
# ═══════════════════════════════════════════════════════════════
class RetryListener:
    async def on_retry(
        self, retry: "RetryManager", exception: Exception, counter: "Counter", backoff: float
    ) -> None: ...

    async def on_attempts_exceeded(self, retry: "RetryManager") -> None: ...

    async def on_success(self, retry: "RetryManager", counter: "Counter") -> None: ...


def register_retry_listener(listener: RetryListener | ListenerFactoryT) -> None:
    """
    Register a listener that will dispatch on all retry components in the system
    """
    global _RETRY_LISTENERS

    _RETRY_LISTENERS.register(listener)



# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: __init__
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.921381+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 3d3cda208efb
# ═══════════════════════════════════════════════════════════════
class RetryManager:
    __slots__ = (
        "_name",
        "_exceptions",
        "_attempts",
        "_backoff",
        "_waiter",
        "_event_dispatcher",
        "_limiter",
    )

    def __init__(
        self,
        name: str,
        exceptions: ExceptionsT,
        attempts: AttemptsT,
        backoff: BackoffsT,
        event_dispatcher: RetryListener,
        limiter: TokenBucket | None = None,
    ) -> None:
        self._name = name
        self._exceptions = exceptions
        self._attempts = attempts
        self._backoff = create_backoff(backoff)
        self._event_dispatcher = event_dispatcher
        self._limiter = limiter

    @property
    def name(self) -> str:
        return self._name

    async def __call__(self, func: FuncT) -> Any:
        counter = create_counter(self._attempts)
        backoff_generator = iter(self._backoff)

        try:
            while bool(counter):
                try:
                    if self._limiter is not None:
                        await self._limiter.take()


# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: _get_meter
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.923117+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: a7dc1ca701a3
# ═══════════════════════════════════════════════════════════════
from hyx.circuitbreaker.events import BreakerListener as BaseBreakerListener
from hyx.fallback.events import FallbackListener as BaseFallbackListener
from hyx.retry.events import RetryListener as BaseRetryListener
from hyx.timeout.events import TimeoutListener as BaseTimeoutListener

try:
    from opentelemetry import metrics
    from opentelemetry.metrics import Meter
except ImportError as e:
    raise ImportError(
        "OpenTelemetry is required for OTel instrumentation. Install it with: pip install hyx[otel]"
    ) from e

if TYPE_CHECKING:
    from hyx.bulkhead.manager import BulkheadManager
    from hyx.circuitbreaker.context import BreakerContext
    from hyx.circuitbreaker.states import BreakerState, FailingState, RecoveringState, WorkingState
    from hyx.fallback.manager import FallbackManager
    from hyx.fallback.typing import ResultT
    from hyx.retry.counters import Counter
    from hyx.retry.manager import RetryManager
    from hyx.timeout.manager import TimeoutManager


METER_NAME = "hyx"


def _get_meter(meter: Meter | None = None) -> Meter:
    return meter if meter is not None else metrics.get_meter(METER_NAME)


class RetryListener(BaseRetryListener):
    """OpenTelemetry metrics listener for retry components."""

    def __init__(self, meter: Meter | None = None) -> None:
        meter = _get_meter(meter)

        self._retry_counter = meter.create_counter(
            name="hyx.retry.attempts",
            description="Number of retry attempts",


# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: __init__
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.925069+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: a49d525cd1d7
# ═══════════════════════════════════════════════════════════════
from hyx.circuitbreaker.events import BreakerListener as BaseBreakerListener
from hyx.fallback.events import FallbackListener as BaseFallbackListener
from hyx.retry.events import RetryListener as BaseRetryListener
from hyx.timeout.events import TimeoutListener as BaseTimeoutListener

try:
    from prometheus_client import REGISTRY, CollectorRegistry, Counter
except ImportError as e:
    raise ImportError(
        "prometheus-client is required for Prometheus instrumentation. Install it with: pip install hyx[prometheus]"
    ) from e

if TYPE_CHECKING:
    from hyx.bulkhead.manager import BulkheadManager
    from hyx.circuitbreaker.context import BreakerContext
    from hyx.circuitbreaker.states import BreakerState, FailingState, RecoveringState, WorkingState
    from hyx.fallback.manager import FallbackManager
    from hyx.fallback.typing import ResultT
    from hyx.retry.counters import Counter as RetryCounter
    from hyx.retry.manager import RetryManager
    from hyx.timeout.manager import TimeoutManager


class RetryListener(BaseRetryListener):
    """Prometheus metrics listener for retry components."""

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        registry = registry if registry is not None else REGISTRY

        self._retry_counter = Counter(
            name="hyx_retry_attempts_total",
            documentation="Number of retry attempts",
            labelnames=["component", "exception"],
            registry=registry,
        )
        self._exhausted_counter = Counter(
            name="hyx_retry_exhausted_total",
            documentation="Number of times retry attempts were exhausted",
            labelnames=["component"],
            registry=registry,


# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: _get_client
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.927020+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 2a1a2f62aa4d
# ═══════════════════════════════════════════════════════════════
from hyx.circuitbreaker.events import BreakerListener as BaseBreakerListener
from hyx.fallback.events import FallbackListener as BaseFallbackListener
from hyx.retry.events import RetryListener as BaseRetryListener
from hyx.timeout.events import TimeoutListener as BaseTimeoutListener

try:
    from statsd import StatsClient  # type: ignore[import-untyped]
except ImportError as e:
    raise ImportError("statsd is required for StatsD instrumentation. Install it with: pip install hyx[statsd]") from e

if TYPE_CHECKING:
    from hyx.bulkhead.manager import BulkheadManager
    from hyx.circuitbreaker.context import BreakerContext
    from hyx.circuitbreaker.states import BreakerState, FailingState, RecoveringState, WorkingState
    from hyx.fallback.manager import FallbackManager
    from hyx.fallback.typing import ResultT
    from hyx.retry.counters import Counter
    from hyx.retry.manager import RetryManager
    from hyx.timeout.manager import TimeoutManager


DEFAULT_PREFIX = "hyx"


def _get_client(client: StatsClient | None = None, prefix: str = DEFAULT_PREFIX) -> StatsClient:
    return client if client is not None else StatsClient(prefix=prefix)


class RetryListener(BaseRetryListener):
    """StatsD metrics listener for retry components."""

    def __init__(self, client: StatsClient | None = None) -> None:
        self._client = _get_client(client)

    async def on_retry(
        self,
        retry: "RetryManager",
        exception: Exception,
        counter: "Counter",
        backoff: float,


# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: get_product_qty_left
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.928802+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 3036851eacc1
# ═══════════════════════════════════════════════════════════════
from hyx.circuitbreaker import consecutive_breaker


class InventoryTemporaryError(RuntimeError):
    """
    Occurs when the inventory microservice is temporary inaccessible
    """


breaker = consecutive_breaker(
    exceptions=(InventoryTemporaryError,),
    failure_threshold=5,
    recovery_time_secs=30,
)


async def get_product_qty_left(product_sku: str) -> dict[str, Any]:
    async with breaker:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://inventory.shop/{product_sku}/")

            if response.status_code >= 500:
                raise InventoryTemporaryError

            return response.json()


asyncio.run(get_product_qty_left("guido-van-rossum-portrait"))



# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: get_product_qty_left
# Source: roma-glushko/hyx
# Harvested: 2026-06-23T16:37:07.930214+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: bbc2993cbc06
# ═══════════════════════════════════════════════════════════════
from hyx.circuitbreaker import consecutive_breaker


class InventoryTemporaryError(RuntimeError):
    """
    Occurs when the inventory microservice is temporary inaccessible
    """


breaker = consecutive_breaker(
    exceptions=(InventoryTemporaryError,),
    failure_threshold=5,
    recovery_time_secs=30,
)


@breaker
async def get_product_qty_left(product_sku: str) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://inventory.shop/{product_sku}/")

        if response.status_code >= 500:
            raise InventoryTemporaryError

        return response.json()


asyncio.run(get_product_qty_left("guido-van-rossum-portrait"))



# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: pybreaker_test_from_pybreaker
# Source: danielfm/pybreaker
# Harvested: 2026-06-23T16:37:25.939062+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 44eb419ae7f9
# ═══════════════════════════════════════════════════════════════
import unittest
from contextlib import contextmanager
from datetime import datetime
from time import sleep
from unittest import mock

import pytest
from pybreaker import *
from tornado import gen, testing


class CircuitBreakerStorageBasedTestCase:
    """Mix in to test against different storage backings. Depends on
    `self.breaker` and `self.breaker_kwargs`.
    """

    def __init__(self):
        self.breaker_kwargs = None

    def test_successful_call(self):
        """CircuitBreaker: it should keep the circuit closed after a successful
        call.
        """

        def func():
            return True

        assert self.breaker.call(func)
        assert self.breaker.fail_counter == 0
        assert self.breaker.current_state == "closed"

    def test_one_failed_call(self):
        """CircuitBreaker: it should keep the circuit closed after a few
        failures.
        """

        def func():
            raise NotImplementedError

        with pytest.raises(NotImplementedError):
            self.breaker.call(func)
        assert self.breaker.fail_counter == 1
        assert self.breaker.current_state == "closed"

    def test_one_successful_call_after_failed_call(self):
        """CircuitBreaker: it should keep the circuit closed after few mixed
        outcomes.
        """

        def suc():
            return True

        def err():
            raise NotImplementedError

        with pytest.raises(NotImplementedError):
            self.breaker.call(err)
        assert self.breaker.fail_counter == 1

        assert self.breaker.call(suc)
        assert self.breaker.fail_counter == 0
        assert self.breaker.current_state == "closed"

    def test_several_failed_calls_setting_absent(self):
        """CircuitBreaker: it should open the circuit after many failures."""
        self.breaker = CircuitBreaker(fail_max=3, **self.breaker_kwargs)

        def func():
            raise NotImplementedError

        with pytest.raises(NotImplementedError):
            self.breaker.call(func)
        with pytest.raises(NotImplementedError):
            self.breaker.call(func)

        # Circuit should open
        with pytest.raises(CircuitBreakerError):
            self.breaker.call(func)
        assert self.breaker.fail_counter == 3
        assert self.breaker.current_state == "open"

    def test_throw_new_error_on_trip_false(self):
        """CircuitBreaker: it should throw the original exception"""
        self.breaker = CircuitBreaker(fail_max=3, **self.breaker_kwargs, throw_new_error_on_trip=False)

        def func():
            raise NotImplementedError

        with pytest.raises(NotImplementedError):
            self.breaker.call(func)
        with pytest.raises(NotImplementedError):
            self.breaker.call(func)
        with pytest.raises(NotImplementedError):
            self.breaker.call(func)

        # Circuit should be open
        assert self.breaker.fail_counter == 3
        assert self.breaker.current_state == "open"

        # Circuit should still be open and break
        with pytest.raises(CircuitBreakerError):
            self.breaker.call(func)
        assert self.breaker.fail_counter == 3
        assert self.breaker.current_state == "open"

    def test_throw_new_error_on_trip_true(self):
        """CircuitBreaker: it should throw a CircuitBreakerError exception"""
        self.breaker = CircuitBreaker(fail_max=3, **self.breaker_kwargs, throw_new_error_on_trip=True)

        def func():
            raise NotImplementedError

        with pytest.raises(NotImplementedError):
            self.breaker.call(func)
        with pytest.raises(NotImplementedError):
            self.breaker.call(func)

        # Circuit should open
        with pytest.raises(CircuitBreakerError):
            self.breaker.call(func)
        assert self.breaker.fail_counter == 3
        assert self.breaker.current_state == "open"

    def test_traceback_in_circuitbreaker_error(self):
        """CircuitBreaker: it should open the circuit after many failures."""
        self.breaker = CircuitBreaker(fail_max=3, **self.breaker_kwargs)

        def func():
            raise NotImplementedError

        with pytest.raises(NotImplementedError):
            self.breaker.call(func)
        with pytest.raises(NotImplementedError):
            self.breaker.call(func)

        # Circuit should open
        try:
            self.breaker.call(func)
            pytest.fail("CircuitBreakerError should throw")
        except CircuitBreakerError:
            import traceback

            assert "NotImplementedError" in traceback.format_exc()
        assert self.breaker.fail_counter == 3
        assert self.breaker.current_state == "open"

    def test_failed_call_after_timeout(self):
        """CircuitBreaker: it should half-open the circuit after timeout."""
        self.breaker = CircuitBreaker(fail_max=3, reset_timeout=0.5, **self.breaker_kwargs)

        def func():
            raise NotImplementedError

        with pytest.raises(NotImplementedError):
            self.breaker.call(func)
        with pytest.raises(NotImplementedError):
            self.breaker.call(func)
        assert self.breaker.current_state == "closed"

        # Circuit should open
        with pytest.raises(CircuitBreakerError):
            self.breaker.call(func)
        assert self.breaker.fail_counter == 3

        # Wait for timeout
        sleep(0.6)

        # Circuit should open again
        with pytest.raises(CircuitBreakerError):
            self.breaker.call(func)
        assert self.breaker.fail_counter == 4
        assert self.breaker.current_state == "open"

    def test_successful_after_timeout(self):
        """CircuitBreaker: it should close the circuit when a call succeeds
        after timeout. The successful function should only be called once.
        """
        self.breaker = CircuitBreaker(fail_max=3, reset_timeout=1, **self.breaker_kwargs)

        suc = mock.MagicMock(return_value=True)

        def err():
            raise NotImplementedError

        with pytest.raises(NotImplementedError):
            self.breaker.call(err)
        with pytest.raises(NotImplementedError):
            self.breaker.call(err)
        assert self.breaker.current_state == "closed"

        # Circuit should open
        with pytest.raises(CircuitBreakerError):
            self.breaker.call(err)
        with pytest.raises(CircuitBreakerError):
            self.breaker.call(suc)
        assert self.breaker.fail_counter == 3

        # Wait for timeout, at least a second since redis rounds to a second
        sleep(2)

        # Circuit should close again
        assert self.breaker.call(suc)
        assert self.breaker.fail_counter == 0
        assert self.breaker.current_state == "closed"
        assert suc.call_count == 1

    def test_failed_call_when_halfopen(self):
        """CircuitBreaker: it should open the circuit when a call fails in
        half-open state.
        """

        def fun():
            raise NotImplementedError

        self.breaker.half_open()
        assert self.breaker.fail_counter == 0
        assert self.breaker.current_state == "half-open"

        # Circuit should open
        with pytest.raises(CircuitBreakerError):
            self.breaker.call(fun)
        assert self.breaker.fail_counter == 1
        assert self.breaker.current_state == "open"

    def test_successful_call_when_halfopen(self):
        """CircuitBreaker: it should close the circuit when a call succeeds in
        half-open state.
        """

        def fun():
            return True

        self.breaker.half_open()
        assert self.breaker.fail_counter == 0
        assert self.breaker.current_state == "half-open"

        # Circuit should open
        assert self.breaker.call(fun)
        assert self.breaker.fail_counter == 0
        assert self.breaker.current_state == "closed"

    def test_close(self):
        """CircuitBreaker: it should allow the circuit to be closed manually."""
        self.breaker = CircuitBreaker(fail_max=3, **self.breaker_kwargs)

        def func():
            raise NotImplementedError

        with pytest.raises(NotImplementedError):
            self.breaker.call(func)
        with pytest.raises(NotImplementedError):
            self.breaker.call(func)

        # Circuit should open
        with pytest.raises(CircuitBreakerError):
            self.breaker.call(func)
        with pytest.raises(CircuitBreakerError):
            self.breaker.call(func)
        assert self.breaker.fail_counter == 3
        assert self.breaker.current_state == "open"

        # Circuit should close again
        self.breaker.close()
        assert self.breaker.fail_counter == 0
        assert self.breaker.current_state == "closed"

    def test_transition_events(self):
        """CircuitBreaker: it should call the appropriate functions on every
        state transition.
        """

        class Listener(CircuitBreakerListener):
            def __init__(self):
                self.out = ""

            def state_change(self, cb, old_state, new_state):
                assert cb
                if old_state:
                    self.out += old_state.name
                if new_state:
                    self.out += "->" + new_state.name
                self.out += ","

        listener = Listener()
        self.breaker = CircuitBreaker(listeners=(listener,), **self.breaker_kwargs)
        assert self.breaker.current_state == "closed"

        self.breaker.open()
        assert self.breaker.current_state == "open"

        self.breaker.half_open()
        assert self.breaker.current_state == "half-open"

        self.breaker.close()
        assert self.breaker.current_state == "closed"

        assert listener.out == "closed->open,open->half-open,half-open->closed,"

    def test_call_events(self):
        """CircuitBreaker: it should call the appropriate functions on every
        successful/failed call.
        """
        self.out = ""

        def suc():
            return True

        def err():
            raise NotImplementedError

        class Listener(CircuitBreakerListener):
            def __init__(self):
                self.out = ""

            def before_call(self, cb, func, *args, **kwargs):
                assert cb
                self.out += "-"

            def success(self, cb):
                assert cb
                self.out += "success"

            def failure(self, cb, exc):
                assert cb
                assert exc
                self.out += "failure"

        listener = Listener()
        self.breaker = CircuitBreaker(listeners=(listener,), **self.breaker_kwargs)

        assert self.breaker.call(suc)
        with pytest.raises(NotImplementedError):
            self.breaker.call(err)
        assert listener.out == "-success-failure"

    def test_generator(self):
        """CircuitBreaker: it should inspect generator values."""

        @self.breaker
        def suc(value):
            "Docstring"
            yield value

        @self.breaker
        def err(value):
            "Docstring"
            x = yield value
            raise NotImplementedError(x)

        s = suc(True)
        e = err(True)
        next(e)

        with pytest.raises(NotImplementedError):
            e.send(True)
        assert self.breaker.fail_counter == 1
        assert next(s)
        with pytest.raises((StopIteration, RuntimeError)):
            next(s)
        assert self.breaker.fail_counter == 0

    def test_contextmanager(self):
        """CircuitBreaker: it should catch in a with statement"""

        class Foo:
            @contextmanager
            @self.breaker
            def wrapper(self):
                try:
                    yield
                except NotImplementedError:
                    raise ValueError

            def foo(self):
                with self.wrapper():
                    raise NotImplementedError

        try:
            Foo().foo()
        except ValueError as e:
            assert isinstance(e, ValueError)


class CircuitBreakerConfigurationTestCase:
    """Tests for the CircuitBreaker class."""

    def test_default_state(self):
        """CircuitBreaker: it should get initial state from state_storage."""
        for state in (STATE_OPEN, STATE_CLOSED, STATE_HALF_OPEN):
            storage = CircuitMemoryStorage(state)
            breaker = CircuitBreaker(state_storage=storage)
            assert breaker.state.name == state

    def test_default_params(self):
        """CircuitBreaker: it should define smart defaults."""
        assert self.breaker.fail_counter == 0
        assert self.breaker.reset_timeout == 60
        assert self.breaker.fail_max == 5
        assert self.breaker.current_state == "closed"
        assert self.breaker.excluded_exceptions == ()
        assert self.breaker.listeners == ()
        assert self.breaker._state_storage.name == "memory"

    def test_new_with_custom_reset_timeout(self):
        """CircuitBreaker: it should support a custom reset timeout value."""
        self.breaker = CircuitBreaker(reset_timeout=30)
        assert self.breaker.fail_counter == 0
        assert self.breaker.reset_timeout == 30
        assert self.breaker.fail_max == 5
        assert self.breaker.excluded_exceptions == ()
        assert self.breaker.listeners == ()
        assert self.breaker._state_storage.name == "memory"

    def test_new_with_custom_fail_max(self):
        """CircuitBreaker: it should support a custom maximum number of
        failures.
        """
        self.breaker = CircuitBreaker(fail_max=10)
        assert self.breaker.fail_counter == 0
        assert self.breaker.reset_timeout == 60
        assert self.breaker.fail_max == 10
        assert self.breaker.excluded_exceptions == ()
        assert self.breaker.listeners == ()
        assert self.breaker._state_storage.name == "memory"

    def test_new_with_custom_excluded_exceptions(self):
        """CircuitBreaker: it should support a custom list of excluded
        exceptions.
        """
        self.breaker = CircuitBreaker(exclude=[Exception])
        assert self.breaker.fail_counter == 0
        assert self.breaker.reset_timeout == 60
        assert self.breaker.fail_max == 5
        assert (Exception,) == self.breaker.excluded_exceptions
        assert self.breaker.listeners == ()
        assert self.breaker._state_storage.name == "memory"

    def test_fail_max_setter(self):
        """CircuitBreaker: it should allow the user to set a new value for
        'fail_max'.
        """
        assert self.breaker.fail_max == 5
        self.breaker.fail_max = 10
        assert self.breaker.fail_max == 10

    def test_reset_timeout_setter(self):
        """CircuitBreaker: it should allow the user to set a new value for
        'reset_timeout'.
        """
        assert self.breaker.reset_timeout == 60
        self.breaker.reset_timeout = 30
        assert self.breaker.reset_timeout == 30

    def test_call_with_no_args(self):
        """CircuitBreaker: it should be able to invoke functions with no-args."""

        def func():
            return True

        assert self.breaker.call(func)

    def test_call_with_args(self):
        """CircuitBreaker: it should be able to invoke functions with args."""

        def func(arg1, arg2):
            return [arg1, arg2]

        assert [42, "abc"], self.breaker.call(func, 42 == "abc")

    def test_call_with_kwargs(self):
        """CircuitBreaker: it should be able to invoke functions with kwargs."""

        def func(**kwargs):
            return kwargs

        assert {"a": 1, "b": 2}, self.breaker.call(func, a=1, b=2)

    @testing.gen_test
    def test_call_async_with_no_args(self):
        """CircuitBreaker: it should be able to invoke async functions with no-args."""

        @gen.coroutine
        def func():
            return True

        ret = yield self.breaker.call(func)
        assert ret

    @testing.gen_test
    def test_call_async_with_args(self):
        """CircuitBreaker: it should be able to invoke async functions with args."""

        @gen.coroutine
        def func(arg1, arg2):
            return [arg1, arg2]

        ret = yield self.breaker.call(func, 42, "abc")
        assert [42, "abc"] == ret

    @testing.gen_test
    def test_call_async_with_kwargs(self):
        """CircuitBreaker: it should be able to invoke async functions with kwargs."""

        @gen.coroutine
        def func(**kwargs):
            return kwargs

        ret = yield self.breaker.call(func, a=1, b=2)
        assert {"a": 1, "b": 2} == ret

    def test_add_listener(self):
        """CircuitBreaker: it should allow the user to add a listener at a
        later time.
        """
        assert self.breaker.listeners == ()

        first = CircuitBreakerListener()
        self.breaker.add_listener(first)
        assert (first,) == self.breaker.listeners

        second = CircuitBreakerListener()
        self.breaker.add_listener(second)
        assert (first, second) == self.breaker.listeners

    def test_add_listeners(self):
        """CircuitBreaker: it should allow the user to add listeners at a
        later time.
        """
        first, second = CircuitBreakerListener(), CircuitBreakerListener()
        self.breaker.add_listeners(first, second)
        assert (first, second) == self.breaker.listeners

    def test_remove_listener(self):
        """CircuitBreaker: it should allow the user to remove a listener."""
        first = CircuitBreakerListener()
        self.breaker.add_listener(first)
        assert (first,) == self.breaker.listeners

        self.breaker.remove_listener(first)
        assert self.breaker.listeners == ()

    def test_excluded_exceptions(self):
        """CircuitBreaker: it should ignore specific exceptions."""
        self.breaker = CircuitBreaker(exclude=[LookupError])

        def err_1():
            raise NotImplementedError

        def err_2():
            raise LookupError

        def err_3():
            raise KeyError

        with pytest.raises(NotImplementedError):
            self.breaker.call(err_1)
        assert self.breaker.fail_counter == 1

        # LookupError is not considered a system error
        with pytest.raises(LookupError):
            self.breaker.call(err_2)
        assert self.breaker.fail_counter == 0

        with pytest.raises(NotImplementedError):
            self.breaker.call(err_1)
        assert self.breaker.fail_counter == 1

        # Should consider subclasses as well (KeyError is a subclass of
        # LookupError)
        with pytest.raises(KeyError):
            self.breaker.call(err_3)
        assert self.breaker.fail_counter == 0

    def test_excluded_callable_exceptions(self):
        """CircuitBreaker: it should ignore specific exceptions that return true from a filtering callable."""

        class TestException(Exception):
            def __init__(self, value):
                self.value = value

        filter_function = lambda e: type(e) == TestException and e.value == "good"
        self.breaker = CircuitBreaker(exclude=[filter_function])

        def err_1():
            raise TestException("bad")

        def err_2():
            raise TestException("good")

        def err_3():
            raise NotImplementedError

        with pytest.raises(TestException):
            self.breaker.call(err_1)
        assert self.breaker.fail_counter == 1

        with pytest.raises(TestException):
            self.breaker.call(err_2)
        assert self.breaker.fail_counter == 0

        with pytest.raises(NotImplementedError):
            self.breaker.call(err_3)
        assert self.breaker.fail_counter == 1

    def test_excluded_callable_and_types_exceptions(self):
        """CircuitBreaker: it should allow a mix of exclusions that includes both filter functions and types."""

        class TestException(Exception):
            def __init__(self, value):
                self.value = value

        filter_function = lambda e: type(e) == TestException and e.value == "good"
        self.breaker = CircuitBreaker(exclude=[filter_function, LookupError])

        def err_1():
            raise TestException("bad")

        def err_2():
            raise TestException("good")

        def err_3():
            raise NotImplementedError

        def err_4():
            raise LookupError

        with pytest.raises(TestException):
            self.breaker.call(err_1)
        assert self.breaker.fail_counter == 1

        with pytest.raises(TestException):
            self.breaker.call(err_2)
        assert self.breaker.fail_counter == 0

        with pytest.raises(NotImplementedError):
            self.breaker.call(err_3)
        assert self.breaker.fail_counter == 1

        with pytest.raises(LookupError):
            self.breaker.call(err_4)
        assert self.breaker.fail_counter == 0

    def test_add_excluded_exception(self):
        """CircuitBreaker: it should allow the user to exclude an exception at a
        later time.
        """
        assert self.breaker.excluded_exceptions == ()

        self.breaker.add_excluded_exception(NotImplementedError)
        assert (NotImplementedError,) == self.breaker.excluded_exceptions

        self.breaker.add_excluded_exception(Exception)
        assert (NotImplementedError, Exception) == self.breaker.excluded_exceptions

    def test_add_excluded_exceptions(self):
        """CircuitBreaker: it should allow the user to exclude exceptions at a
        later time.
        """
        self.breaker.add_excluded_exceptions(NotImplementedError, Exception)
        assert (NotImplementedError, Exception) == self.breaker.excluded_exceptions

    def test_remove_excluded_exception(self):
        """CircuitBreaker: it should allow the user to remove an excluded
        exception.
        """
        self.breaker.add_excluded_exception(NotImplementedError)
        assert (NotImplementedError,) == self.breaker.excluded_exceptions

        self.breaker.remove_excluded_exception(NotImplementedError)
        assert self.breaker.excluded_exceptions == ()

    def test_decorator(self):
        """CircuitBreaker: it should be a decorator."""

        @self.breaker
        def suc(value):
            "Docstring"
            return value

        @self.breaker
        def err(value):
            "Docstring"
            raise NotImplementedError

        assert suc.__doc__ == "Docstring"
        assert err.__doc__ == "Docstring"
        assert suc.__name__ == "suc"
        assert err.__name__ == "err"

        with pytest.raises(NotImplementedError):
            err(True)
        assert self.breaker.fail_counter == 1

        assert suc(True)
        assert self.breaker.fail_counter == 0

    @testing.gen_test
    def test_decorator_call_future(self):
        """CircuitBreaker: it should be a decorator."""

        @self.breaker(__pybreaker_call_async=True)
        @gen.coroutine
        def suc(value):
            "Docstring"
            raise gen.Return(value)

        @self.breaker(__pybreaker_call_async=True)
        @gen.coroutine
        def err(value):
            "Docstring"
            raise NotImplementedError

        assert suc.__doc__ == "Docstring"
        assert err.__doc__ == "Docstring"
        assert suc.__name__ == "suc"
        assert err.__name__ == "err"

        with pytest.raises(NotImplementedError):
            yield err(True)

        assert self.breaker.fail_counter == 1

        ret = yield suc(True)
        assert ret
        assert self.breaker.fail_counter == 0

    @mock.patch("pybreaker.HAS_TORNADO_SUPPORT", False)
    def test_no_tornado_raises(self):
        with pytest.raises(ImportError):

            def func():
                return True

            self.breaker(func, __pybreaker_call_async=True)

    def test_name(self):
        """CircuitBreaker: it should allow an optional name to be set and
        retrieved.
        """
        name = "test_breaker"
        self.breaker = CircuitBreaker(name=name)
        assert self.breaker.name == name

        name = "breaker_test"
        self.breaker.name = name
        assert self.breaker.name == name

    def test_success_threshold_default_behavior(self):
        """CircuitBreaker: it should maintain backward compatibility with default success_threshold=1."""
        self.breaker = CircuitBreaker(fail_max=3, reset_timeout=0.1, **self.breaker_kwargs)

        def fun():
            return True

        def err():
            raise NotImplementedError

        # Open the circuit
        for i in range(3):
            if i < 2:
                with pytest.raises(NotImplementedError):
                    self.breaker.call(err)
            else:
                with pytest.raises(CircuitBreakerError):
                    self.breaker.call(err)

        # Wait for timeout to enter half-open state
        sleep(0.2)

        # Single successful call should close the circuit (default behavior)
        assert self.breaker.call(fun)
        assert self.breaker.current_state == "closed"
        assert self.breaker.success_counter == 0  # Should be reset when closed

    def test_success_threshold_multiple_successes_required(self):
        """CircuitBreaker: it should require multiple successful calls before closing when success_threshold > 1."""
        self.breaker = CircuitBreaker(fail_max=3, reset_timeout=0.1, success_threshold=3, **self.breaker_kwargs)

        def fun():
            return True

        def err():
            raise NotImplementedError

        # Open the circuit
        for i in range(3):
            if i < 2:
                with pytest.raises(NotImplementedError):
                    self.breaker.call(err)
            else:
                with pytest.raises(CircuitBreakerError):
                    self.breaker.call(err)

        # Wait for timeout to enter half-open state
        sleep(0.2)

        # First successful call should not close the circuit
        assert self.breaker.call(fun)
        assert self.breaker.current_state == "half-open"
        assert self.breaker.success_counter == 1

        # Second successful call should not close the circuit
        assert self.breaker.call(fun)
        assert self.breaker.current_state == "half-open"
        assert self.breaker.success_counter == 2

        # Third successful call should close the circuit
        assert self.breaker.call(fun)
        assert self.breaker.current_state == "closed"
        assert self.breaker.success_counter == 0  # Should be reset when closed

    def test_success_threshold_failure_resets_counter(self):
        """CircuitBreaker: it should reset success counter when a failure occurs in half-open state."""
        self.breaker = CircuitBreaker(fail_max=3, reset_timeout=0.1, success_threshold=3, **self.breaker_kwargs)

        def fun():
            return True

        def err():
            raise NotImplementedError

        # Open the circuit
        for i in range(3):
            if i < 2:
                with pytest.raises(NotImplementedError):
                    self.breaker.call(err)
            else:
                with pytest.raises(CircuitBreakerError):
                    self.breaker.call(err)

        # Wait for timeout to enter half-open state
        sleep(0.2)

        # First successful call
        assert self.breaker.call(fun)
        assert self.breaker.current_state == "half-open"
        assert self.breaker.success_counter == 1

        # Second successful call
        assert self.breaker.call(fun)
        assert self.breaker.current_state == "half-open"
        assert self.breaker.success_counter == 2

        # Failure should reset success counter and open circuit
        with pytest.raises(CircuitBreakerError):
            self.breaker.call(err)
        assert self.breaker.current_state == "open"
        assert self.breaker.success_counter == 0  # Should be reset when opened

    def test_success_threshold_property(self):
        """CircuitBreaker: it should support getting and setting success_threshold."""
        self.breaker = CircuitBreaker(success_threshold=5)
        assert self.breaker.success_threshold == 5

        self.breaker.success_threshold = 10
        assert self.breaker.success_threshold == 10

    def test_success_threshold_redis_storage(self):
        """CircuitBreaker: it should work correctly with Redis storage."""
        # This test requires Redis to be running
        try:
            import redis

            redis_client = redis.Redis()
            redis_client.ping()
        except (ImportError, redis.ConnectionError):
            pytest.skip("Redis not available")

        storage = CircuitRedisStorage(STATE_CLOSED, redis_client)
        self.breaker = CircuitBreaker(fail_max=3, reset_timeout=0.1, success_threshold=2, state_storage=storage)

        def fun():
            return True

        def err():
            raise NotImplementedError

        # Open the circuit
        for i in range(3):
            if i < 2:
                with pytest.raises(NotImplementedError):
                    self.breaker.call(err)
            else:
                with pytest.raises(CircuitBreakerError):
                    self.breaker.call(err)

        # Wait for timeout to enter half-open state
        sleep(0.2)

        # First successful call should not close the circuit
        assert self.breaker.call(fun)
        assert self.breaker.current_state == "half-open"
        assert self.breaker.success_counter == 1

        # Second successful call should close the circuit
        assert self.breaker.call(fun)
        assert self.breaker.current_state == "closed"
        assert self.breaker.success_counter == 0


class CircuitBreakerTestCase(
    testing.AsyncTestCase,
    CircuitBreakerStorageBasedTestCase,
    CircuitBreakerConfigurationTestCase,
):
    """Tests for the CircuitBreaker class."""

    def setUp(self):
        super(CircuitBreakerTestCase, self).setUp()
        self.breaker_kwargs = {}
        self.breaker = CircuitBreaker()

    def test_create_new_state__bad_state(self):
        with pytest.raises(ValueError):
            self.breaker._create_new_state("foo")

    @mock.patch("pybreaker.CircuitOpenState")
    def test_notify_not_called_on_init(self, open_state):
        storage = CircuitMemoryStorage("open")
        breaker = CircuitBreaker(state_storage=storage)
        open_state.assert_called_once_with(breaker, prev_state=None, notify=False)

    @mock.patch("pybreaker.CircuitOpenState")
    def test_notify_called_on_state_change(self, open_state):
        storage = CircuitMemoryStorage("closed")
        breaker = CircuitBreaker(state_storage=storage)
        prev_state = breaker.state
        breaker.state = "open"
        open_state.assert_called_once_with(breaker, prev_state=prev_state, notify=True)

    def test_failure_count_not_reset_during_creation(self):
        for state in (STATE_OPEN, STATE_CLOSED, STATE_HALF_OPEN):
            storage = CircuitMemoryStorage(state)
            storage.increment_counter()

            breaker = CircuitBreaker(state_storage=storage)
            assert breaker.state.name == state
            assert breaker.fail_counter == 1

    def test_state_opened_at_not_reset_during_creation(self):
        for state in (STATE_OPEN, STATE_CLOSED, STATE_HALF_OPEN):
            storage = CircuitMemoryStorage(state)
            now = datetime.now()
            storage.opened_at = now

            breaker = CircuitBreaker(state_storage=storage)
            assert breaker.state.name == state
            assert storage.opened_at == now


import logging

import fakeredis
from redis.exceptions import RedisError


class CircuitBreakerRedisTestCase(unittest.TestCase, CircuitBreakerStorageBasedTestCase):
    """Tests for the CircuitBreaker class."""

    def setUp(self):
        self.redis = fakeredis.FakeStrictRedis()
        self.breaker_kwargs = {"state_storage": CircuitRedisStorage("closed", self.redis)}
        self.breaker = CircuitBreaker(**self.breaker_kwargs)

    def tearDown(self):
        self.redis.flushall()

    def test_namespace(self):
        self.redis.flushall()
        self.breaker_kwargs = {"state_storage": CircuitRedisStorage("closed", self.redis, namespace="my_app")}
        self.breaker = CircuitBreaker(**self.breaker_kwargs)

        def func():
            raise NotImplementedError

        with pytest.raises(NotImplementedError):
            self.breaker.call(func)
        keys = self.redis.keys()
        assert len(keys) == 3  # fail_counter, success_counter, state
        assert keys[0].decode("utf-8").startswith("my_app")
        assert keys[1].decode("utf-8").startswith("my_app")
        assert keys[2].decode("utf-8").startswith("my_app")

    def test_fallback_state(self):
        logger = logging.getLogger("pybreaker")
        logger.setLevel(logging.FATAL)
        self.breaker_kwargs = {
            "state_storage": CircuitRedisStorage("closed", self.redis, fallback_circuit_state="open")
        }
        self.breaker = CircuitBreaker(**self.breaker_kwargs)

        def func(k):
            raise RedisError()

        with mock.patch.object(self.redis, "get", new=func):
            state = self.breaker.state
            assert state.name == "open"

    def test_missing_state(self):
        """CircuitBreakerRedis: If state on Redis is missing, it should set the
        fallback circuit state and reset the fail counter to 0.
        """
        self.breaker_kwargs = {
            "state_storage": CircuitRedisStorage("closed", self.redis, fallback_circuit_state="open")
        }
        self.breaker = CircuitBreaker(**self.breaker_kwargs)

        def func():
            raise NotImplementedError

        with pytest.raises(NotImplementedError):
            self.breaker.call(func)
        assert self.breaker.fail_counter == 1

        with mock.patch.object(self.redis, "get", new=lambda k: None):
            state = self.breaker.state
            assert state.name == "open"
            assert self.breaker.fail_counter == 0

    def test_cluster_mode(self):
        self.redis.flushall()

        storage = CircuitRedisStorage(STATE_OPEN, self.redis, namespace="my_app", cluster_mode=True)
        breaker_kwargs = {"state_storage": storage}

        now = datetime.now()
        storage.opened_at = now

        now_str = now.strftime("%Y-%m-%d-%H:%M:%S")
        opened_at = storage.opened_at.strftime("%Y-%m-%d-%H:%M:%S")

        breaker = CircuitBreaker(**breaker_kwargs)
        assert breaker.state.name == STATE_OPEN
        assert opened_at == now_str


import threading
from types import MethodType


class CircuitBreakerThreadsTestCase(unittest.TestCase):
    """Tests to reproduce common synchronization errors on CircuitBreaker class."""

    def setUp(self):
        self.breaker = CircuitBreaker(fail_max=3000, reset_timeout=1)

    def _start_threads(self, target, n):
        """Starts `n` threads that calls `target` and waits for them to finish."""
        threads = [threading.Thread(target=target) for i in range(n)]
        [t.start() for t in threads]
        [t.join() for t in threads]

    def _mock_function(self, obj, func):
        """Replaces a bounded function in `self.breaker` by another."""
        setattr(obj, func.__name__, MethodType(func, self.breaker))

    def test_fail_thread_safety(self):
        """CircuitBreaker: it should compute a failed call atomically to
        avoid race conditions.
        """

        # Create a specific exception to avoid masking other errors
        class SpecificException(Exception):
            pass

        @self.breaker
        def err():
            raise SpecificException

        def trigger_error():
            for n in range(500):
                try:
                    err()
                except SpecificException:
                    pass

        def _inc_counter(self):
            c = self._state_storage._fail_counter
            sleep(0.00005)
            self._state_storage._fail_counter = c + 1

        self._mock_function(self.breaker, _inc_counter)
        self._start_threads(trigger_error, 3)
        assert self.breaker.fail_counter == 1500

    def test_success_thread_safety(self):
        """CircuitBreaker: it should compute a successful call atomically
        to avoid race conditions.
        """

        @self.breaker
        def suc():
            return True

        def trigger_success():
            for n in range(500):
                suc()

        class SuccessListener(CircuitBreakerListener):
            def success(self, cb):
                c = 0
                if hasattr(cb, "_success_counter"):
                    c = cb._success_counter
                sleep(0.00005)
                cb._success_counter = c + 1

        self.breaker.add_listener(SuccessListener())
        self._start_threads(trigger_success, 3)
        assert self.breaker._success_counter == 1500

    def test_half_open_thread_safety(self):
        """CircuitBreaker: it should allow only one trial call when the
        circuit is half-open.
        """
        self.breaker = CircuitBreaker(fail_max=1, reset_timeout=0.01)

        self.breaker.open()
        sleep(0.01)

        @self.breaker
        def err():
            raise Exception

        def trigger_failure():
            try:
                err()
            except:
                pass

        class StateListener(CircuitBreakerListener):
            def __init__(self):
                self._count = 0

            def before_call(self, cb, fun, *args, **kwargs):
                sleep(0.00005)

            def state_change(self, cb, old_state, new_state):
                if new_state.name == "half-open":
                    self._count += 1

        state_listener = StateListener()
        self.breaker.add_listener(state_listener)

        self._start_threads(trigger_failure, 5)
        assert state_listener._count == 1

    def test_fail_max_thread_safety(self):
        """CircuitBreaker: it should not allow more failed calls than
        'fail_max' setting.
        """

        @self.breaker
        def err():
            raise Exception

        def trigger_error():
            for i in range(2000):
                try:
                    err()
                except:
                    pass

        class SleepListener(CircuitBreakerListener):
            def before_call(self, cb, func, *args, **kwargs):
                sleep(0.00005)

        self.breaker.add_listener(SleepListener())
        self._start_threads(trigger_error, 3)
        assert self.breaker.fail_max == self.breaker.fail_counter


class CircuitBreakerRedisConcurrencyTestCase(unittest.TestCase):
    """Tests to reproduce common concurrency between different machines
    connecting to redis. This is simulated locally using threads.
    """

    def setUp(self):
        self.redis = fakeredis.FakeStrictRedis()
        self.breaker_kwargs = {
            "fail_max": 3000,
            "reset_timeout": 1,
            "state_storage": CircuitRedisStorage("closed", self.redis),
        }
        self.breaker = CircuitBreaker(**self.breaker_kwargs)

    def tearDown(self):
        self.redis.flushall()

    def _start_threads(self, target, n):
        """Starts `n` threads that calls `target` and waits for them to finish."""
        threads = [threading.Thread(target=target) for i in range(n)]
        [t.start() for t in threads]
        [t.join() for t in threads]

    def _mock_function(self, obj, func):
        """Replaces a bounded function in `self.breaker` by another."""
        setattr(obj, func.__name__, MethodType(func, self.breaker))

    def test_fail_thread_safety(self):
        """CircuitBreaker: it should compute a failed call atomically to
        avoid race conditions.
        """

        # Create a specific exception to avoid masking other errors
        class SpecificException(Exception):
            pass

        @self.breaker
        def err():
            raise SpecificException

        def trigger_error():
            for n in range(500):
                try:
                    err()
                except SpecificException:
                    pass

        def _inc_counter(self):
            sleep(0.00005)
            self._state_storage.increment_counter()

        self._mock_function(self.breaker, _inc_counter)
        self._start_threads(trigger_error, 3)
        assert self.breaker.fail_counter == 1500

    def test_success_thread_safety(self):
        """CircuitBreaker: it should compute a successful call atomically
        to avoid race conditions.
        """

        @self.breaker
        def suc():
            return True

        def trigger_success():
            for n in range(500):
                suc()

        class SuccessListener(CircuitBreakerListener):
            def success(self, cb):
                c = 0
                if hasattr(cb, "_success_counter"):
                    c = cb._success_counter
                sleep(0.00005)
                cb._success_counter = c + 1

        self.breaker.add_listener(SuccessListener())
        self._start_threads(trigger_success, 3)
        assert self.breaker._success_counter == 1500

    def test_half_open_thread_safety(self):
        """CircuitBreaker: it should allow only one trial call when the
        circuit is half-open.
        """
        self.breaker = CircuitBreaker(fail_max=1, reset_timeout=0.01)

        self.breaker.open()
        sleep(0.01)

        @self.breaker
        def err():
            raise Exception

        def trigger_failure():
            try:
                err()
            except:
                pass

        class StateListener(CircuitBreakerListener):
            def __init__(self):
                self._count = 0

            def before_call(self, cb, fun, *args, **kwargs):
                sleep(0.00005)

            def state_change(self, cb, old_state, new_state):
                if new_state.name == "half-open":
                    self._count += 1

        state_listener = StateListener()
        self.breaker.add_listener(state_listener)

        self._start_threads(trigger_failure, 5)
        assert state_listener._count == 1

    def test_fail_max_thread_safety(self):
        """CircuitBreaker: it should not allow more failed calls than 'fail_max'
        setting. Note that with Redis, where we have separate systems
        incrementing the counter, we can get concurrent updates such that the
        counter is greater than the 'fail_max' by the number of systems. To
        prevent this, we'd need to take out a lock amongst all systems before
        trying the call.
        """

        @self.breaker
        def err():
            raise Exception

        def trigger_error():
            for i in range(2000):
                try:
                    err()
                except:
                    pass

        class SleepListener(CircuitBreakerListener):
            def before_call(self, cb, func, *args, **kwargs):
                sleep(0.00005)

        self.breaker.add_listener(SleepListener())
        num_threads = 3
        self._start_threads(trigger_error, num_threads)
        assert self.breaker.fail_counter < self.breaker.fail_max + num_threads


class CircuitBreakerContextManagerTestCase(unittest.TestCase):
    """Tests for the CircuitBreaker class, when used as a context manager."""

    def test_calling(self):
        """Test that the CircuitBreaker calling() API returns a context manager and works as expected."""

        class TestError(Exception):
            pass

        breaker = CircuitBreaker(fail_max=2, reset_timeout=0.01)
        mock_fn = mock.MagicMock()

        def _do_raise():
            with breaker.calling():
                raise TestError

        def _do_succeed():
            with breaker.calling():
                mock_fn()

        self.assertRaises(TestError, _do_raise)
        self.assertRaises(CircuitBreakerError, _do_raise)
        assert breaker.fail_counter == 2
        assert breaker.current_state == "open"

        # Still fails while circuit breaker is open:
        self.assertRaises(CircuitBreakerError, _do_succeed)
        mock_fn.assert_not_called()

        sleep(0.01)

        _do_succeed()
        mock_fn.assert_called_once()
        assert breaker.fail_counter == 0
        assert breaker.current_state == "closed"


if __name__ == "__main__":
    unittest.main()



# ═══════════════════════════════════════════════════════════════
# 🦞 Predator Nutrient: __init___from_pybreaker
# Source: danielfm/pybreaker
# Harvested: 2026-06-23T16:37:25.961201+00:00
# Status: EXPERIMENTAL — not production-safe until reviewed
# Hash: 89cf0586c0ae
# ═══════════════════════════════════════════════════════════════
"""Threadsafe pure-Python implementation of the Circuit Breaker pattern, described
by Michael T. Nygard in his book 'Release It!'.

For more information on this and other patterns and best practices, buy the
book at https://pragprog.com/titles/mnee2/release-it-second-edition/
"""

from __future__ import annotations

import calendar
import contextlib
import logging
import sys
import threading
import time
import types
from abc import abstractmethod
from datetime import datetime, timedelta
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Literal,
    NoReturn,
    TypeVar,
    Union,
    cast,
    overload,
)

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Sequence

# For compatibility with Python 3.10 and earlier.
# Otherwise, `from datetime import UTC` would suffice.
try:
    from datetime import UTC  # type: ignore[attr-defined]
except ImportError:
    from datetime import timezone

    UTC = timezone.utc

try:
    from tornado import gen

    HAS_TORNADO_SUPPORT = True
except ImportError:
    HAS_TORNADO_SUPPORT = False

try:
    from redis import Redis
    from redis.client import Pipeline
    from redis.exceptions import RedisError

    HAS_REDIS_SUPPORT = True
except ImportError:
    HAS_REDIS_SUPPORT = False

__all__ = (
    "CircuitBreaker",
    "CircuitBreakerListener",
    "CircuitBreakerError",
    "CircuitMemoryStorage",
    "CircuitRedisStorage",
    "STATE_OPEN",
    "STATE_CLOSED",
    "STATE_HALF_OPEN",
)

STATE_OPEN = "open"
STATE_CLOSED = "closed"
STATE_HALF_OPEN = "half-open"

T = TypeVar("T")
ExceptionType = TypeVar("ExceptionType", bound=BaseException)
CBListenerType = TypeVar("CBListenerType", bound="CircuitBreakerListener")
CBStateType = Union["CircuitClosedState", "CircuitHalfOpenState", "CircuitOpenState"]


class CircuitBreaker:
    """More abstractly, circuit breakers exists to allow one subsystem to fail
    without destroying the entire system.

    This is done by wrapping dangerous operations (typically integration points)
    with a component that can circumvent calls when the system is not healthy.

    This pattern is described by Michael T. Nygard in his book 'Release It!'.
    """

    def __init__(
        self,
        fail_max: int = 5,
        reset_timeout: float = 60,
        success_threshold: int = 1,
        exclude: Iterable[type[ExceptionType] | Callable[[Any], bool]] | None = None,
        listeners: Sequence[CBListenerType] | None = None,
        state_storage: CircuitBreakerStorage | None = None,
        name: str | None = None,
        throw_new_error_on_trip: bool = True,
    ) -> None:
        """Create a new circuit breaker with the given parameters."""
        self._lock = threading.RLock()
        self._state_storage = state_storage or CircuitMemoryStorage(STATE_CLOSED)
        self._state = self._create_new_state(self.current_state)

        self._fail_max = fail_max
        self._reset_timeout = reset_timeout
        self._success_threshold = success_threshold

        self._excluded_exceptions = list(exclude or [])
        self._listeners = list(listeners or [])
        self._name = name

        self._throw_new_error_on_trip = throw_new_error_on_trip

    @property
    def fail_counter(self) -> int:
        """Return the current number of consecutive failures."""
        return self._state_storage.counter

    @property
    def success_counter(self) -> int:
        """Return the current number of consecutive successes in half-open state."""
        return self._state_storage.success_counter

    @property
    def fail_max(self) -> int:
        """Return the maximum number of failures tolerated before the circuit is opened."""
        return self._fail_max

    @fail_max.setter
    def fail_max(self, number: int) -> None:
        """Set the maximum `number` of failures tolerated before the circuit is opened."""
        self._fail_max = number

    @property
    def reset_timeout(self) -> float:
        """Once this circuit breaker is opened, it should remain opened until the
        timeout period, in seconds, elapses.
        """
        return self._reset_timeout

    @reset_timeout.setter
    def reset_timeout(self, timeout: float) -> None:
        """Set the `timeout` period, in seconds, this circuit breaker should be kept open."""
        self._reset_timeout = timeout

    @property
    def success_threshold(self) -> int:
        """Return the number of successful requests required before transitioning from half-open to closed state."""
        return self._success_threshold

    @success_threshold.setter
    def success_threshold(self, threshold: int) -> None:
        """Set the number of successful requests required before transitioning from half-open to closed state."""
        self._success_threshold = threshold

    def _create_new_state(
        self,
        new_state: str,
        prev_state: CircuitBreakerState | None = None,
        notify: bool = False,
    ) -> CBStateType:
        """Return state object from state string, i.e., 'closed' -> <CircuitClosedState>."""
        state_map: dict[str, type[CBStateType]] = {
            STATE_CLOSED: CircuitClosedState,
            STATE_OPEN: CircuitOpenState,
            STATE_HALF_OPEN: CircuitHalfOpenState,
        }
        try:
            cls = state_map[new_state]
            return cls(self, prev_state=prev_state, notify=notify)
        except KeyError as e:
            msg = "Unknown state {!r}, valid states: {}"
            raise ValueError(msg.format(new_state, ", ".join(state_map))) from e

    @property
    def state(self) -> CBStateType:
        """Update (if needed) and returns the cached state object."""
        # Ensure cached state is up-to-date
        if self.current_state != self._state.name:
            # If cached state is out-of-date, that means that it was likely
            # changed elsewhere (e.g. another process instance). We still send
            # out a notification, informing others that this particular circuit
            # breaker instance noticed the changed circuit.
            self.state = self.current_state  # type: ignore[assignment]
        return self._state

    @state.setter
    def state(self, state_str: str) -> None:
        """Set cached state and notify listeners of newly cached state."""
        with self._lock:
            self._state = self._create_new_state(state_str, prev_state=self._state, notify=True)

    @property
    def current_state(self) -> str:
        """Return a string that identifies the state of the circuit breaker as
        reported by the _state_storage. i.e., 'closed', 'open', 'half-open'.
        """
        return self._state_storage.state

    @property
    def excluded_exceptions(
        self,
    ) -> tuple[type[ExceptionType] | Callable[[Any], bool], ...]:
        """Return the list of excluded exceptions, e.g., exceptions that should
        not be considered system errors by this circuit breaker.
        """
        return tuple(self._excluded_exceptions)

    def add_excluded_exception(self, exception: type[ExceptionType]) -> None:
        """Add an exception to the list of excluded exceptions."""
        with self._lock:
            self._excluded_exceptions.append(exception)

    def add_excluded_exceptions(self, *exceptions: type[ExceptionType]) -> None:
        """Add exceptions to the list of excluded exceptions."""
        for exc in exceptions:
            self.add_excluded_exception(exc)

    def remove_excluded_exception(self, exception: type[ExceptionType]) -> None:
        """Remove an exception from the list of excluded exceptions."""
        with self._lock:
            self._excluded_exceptions.remove(exception)

    def _inc_counter(self) -> None:
        """Increment the counter of failed calls."""
        self._state_storage.increment_counter()

    def is_system_error(self, exception: ExceptionType) -> bool:
        """Return whether the exception `exception` is considered a signal of
        system malfunction. Business exceptions should not cause this circuit
        breaker to open.
        """
        exception_type = type(exception)
        for exclusion in self._excluded_exceptions:
            if type(exclusion) is type:
                if issubclass(exception_type, exclusion):
                    return False
            elif callable(exclusion):
                if exclusion(exception):
                    return False
        return True

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Call `func` with the given `args` and `kwargs` according to the rules
        implemented by the current state of this circuit breaker.
        """
        with self._lock:
            return self.state.call(func, *args, **kwargs)

    @contextlib.contextmanager
    def calling(self) -> Any:
        """Return a context manager, enabling the circuit breaker to be used with a
        `with` statement. The block of code inside the `with` statement will be
        executed according to the rules implemented by the current state of this
        circuit breaker.
        """

        def _wrapper() -> Generator:
            yield

        yield from self.call(_wrapper)

    def call_async(self, func, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Call async `func` with the given `args` and `kwargs` according to the rules
        implemented by the current state of this circuit breaker.

        Return a closure to prevent import errors when using without tornado present
        """

        @gen.coroutine
        def wrapped():  # type: ignore[no-untyped-def]
            with self._lock:
                ret = yield self.state.call_async(func, *args, **kwargs)
                raise gen.Return(ret)

        return wrapped()

    def open(self) -> bool:
        """Open the circuit, e.g., the following calls will immediately fail until timeout elapses."""
        with self._lock:
            self._state_storage.opened_at = datetime.now(UTC)
            self.state = self._state_storage.state = STATE_OPEN  # type: ignore[assignment]

            return self._throw_new_error_on_trip

    def half_open(self) -> None:
        """Half-open the circuit, e.g. lets the following call pass through and
        opens the circuit if the call fails (or closes the circuit if the call
        succeeds).
        """
        with self._lock:
            self.state = self._state_storage.state = STATE_HALF_OPEN  # type: ignore[assignment]

    def close(self) -> None:
        """Close the circuit, e.g. lets the following calls execute as usual."""
        with self._lock:
            self._state_storage.reset_success_counter()  # Reset success counter when closing
            self.state = self._state_storage.state = STATE_CLOSED  # type: ignore[assignment]

    def __call__(self, *call_args: Any, **call_kwargs: bool) -> Callable:
        """Return a wrapper that calls the function `func` according to the rules
        implemented by the current state of this circuit breaker.

        Optionally takes the keyword argument `__pybreaker_call_coroutine`,
        which will will call `func` as a Tornado co-routine.
        """
        call_async = call_kwargs.pop("__pybreaker_call_async", False)

        if call_async and not HAS_TORNADO_SUPPORT:
            message = "No module named tornado"
            raise ImportError(message)

        def _outer_wrapper(func):  # type: ignore[no-untyped-def]
            @wraps(func)
            def _inner_wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
                if call_async:
                    return self.call_async(func, *args, **kwargs)
                return self.call(func, *args, **kwargs)

            return _inner_wrapper

        if call_args:
            return _outer_wrapper(*call_args)
        return _outer_wrapper

    @property
    def listeners(self) -> tuple[CBListenerType, ...]:
        """Return the registered listeners as a tuple."""
        return tuple(self._listeners)  # type: ignore[arg-type]

    def add_listener(self, listener: CBListenerType) -> None:
        """Register a listener for this circuit breaker."""
        with self._lock:
            self._listeners.append(listener)  # type: ignore[arg-type]

    def add_listeners(self, *listeners: CBListenerType) -> None:
        """Register listeners for this circuit breaker."""
        for listener in listeners:
            self.add_listener(listener)

    def remove_listener(self, listener: CBListenerType) -> None:
        """Unregister a listener of this circuit breaker."""
        with self._lock:
            self._listeners.remove(listener)  # type: ignore[arg-type]

    @property
    def name(self) -> str | None:
        """Return the name of this circuit breaker. Useful for logging."""
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        """Set the name of this circuit breaker."""
        self._name = name


class CircuitBreakerStorage:
    """Define the underlying storage for a circuit breaker - the underlying
    implementation should be in a subclass that overrides the method this
    class defines.
    """

    def __init__(self, name: str) -> None:
        """Create a new instance identified by `name`."""
        self._name = name

    @property
    def name(self) -> str:
        """Return a human friendly name that identifies this state."""
        return self._name

    @property
    @abstractmethod
    def state(self) -> str:
        """Override this method to retrieve the current circuit breaker state."""

    @state.setter
    def state(self, state: str) -> None:
        """Override this method to set the current circuit breaker state."""

    def increment_counter(self) -> None:
        """Override this method to increase the failure counter by one."""

    def reset_counter(self) -> None:
        """Override this method to set the failure counter to zero."""

    def increment_success_counter(self) -> None:
        """Override this method to increase the success counter by one."""

    def reset_success_counter(self) -> None:
        """Override this method to set the success counter to zero."""

    @property
    @abstractmethod
    def counter(self) -> int:
        """Override this method to retrieve the current value of the failure counter."""

    @property
    @abstractmethod
    def success_counter(self) -> int:
        """Override this method to retrieve the current value of the success counter."""

    @property
    @abstractmethod
    def opened_at(self) -> datetime | None:
        """Override this method to retrieve the most recent value of when the circuit was opened."""

    @opened_at.setter
    def opened_at(self, datetime: datetime) -> None:
        """Override this method to set the most recent value of when the circuit was opened."""


class CircuitMemoryStorage(CircuitBreakerStorage):
    """Implement a `CircuitBreakerStorage` in local memory."""

    def __init__(self, state: str) -> None:
        """Create a new instance with the given `state`."""
        super().__init__("memory")
        self._fail_counter = 0
        self._success_counter = 0
        self._opened_at: datetime | None = None
        self._state = state

    @property
    def state(self) -> str:
        """Return the current circuit breaker state."""
        return self._state

    @state.setter
    def state(self, state: str) -> None:
        """Set the current circuit breaker state to `state`."""
        self._state = state

    def increment_counter(self) -> None:
        """Increase the failure counter by one."""
        self._fail_counter += 1

    def reset_counter(self) -> None:
        """Set the failure counter to zero."""
        self._fail_counter = 0

    def increment_success_counter(self) -> None:
        """Increase the success counter by one."""
        self._success_counter += 1

    def reset_success_counter(self) -> None:
        """Set the success counter to zero."""
        self._success_counter = 0

    @property
    def counter(self) -> int:
        """Return the current value of the failure counter."""
        return self._fail_counter

    @property
    def success_counter(self) -> int:
        """Return the current value of the success counter."""
        return self._success_counter

    @property
    def opened_at(self) -> datetime | None:
        """Return the most recent value of when the circuit was opened."""
        return self._opened_at

    @opened_at.setter
    def opened_at(self, datetime: datetime) -> None:
        """Set the most recent value of when the circuit was opened to `datetime`."""
        self._opened_at = datetime


class CircuitRedisStorage(CircuitBreakerStorage):
    """Implement a `CircuitBreakerStorage` using redis."""

    BASE_NAMESPACE = "pybreaker"

    logger = logging.getLogger(__name__)

    def __init__(
        self,
        state: str,
        redis_object: Redis,
        namespace: str | None = None,
        fallback_circuit_state: str = STATE_CLOSED,
        cluster_mode: bool = False,
    ):
        """Create a new instance with the given `state` and `redis` object. The
        redis object should be similar to pyredis' StrictRedis class. If there
        are any connection issues with redis, the `fallback_circuit_state` is
        used to determine the state of the circuit.
        """
        # Module does not exist, so this feature is not available
        if not HAS_REDIS_SUPPORT:
            message = "CircuitRedisStorage can only be used if the required dependencies exist"
            raise ImportError(message)

        super().__init__("redis")

        self._redis = redis_object
        self._namespace_name = namespace
        self._fallback_circuit_state = fallback_circuit_state
        self._initial_state = str(state)
        self._cluster_mode = cluster_mode

        self._initialize_redis_state(self._initial_state)

    def _initialize_redis_state(self, state: str) -> None:
        self._redis.setnx(self._namespace("fail_counter"), 0)
        self._redis.setnx(self._namespace("success_counter"), 0)
        self._redis.setnx(self._namespace("state"), state)

    @property
    def state(self) -> str:
        """Return the current circuit breaker state.

        If the circuit breaker state on Redis is missing, re-initialize it
        with the fallback circuit state and reset the fail counter.
        """
        try:
            state_bytes: bytes | None = self._redis.get(self._namespace("state"))
        except RedisError:
            self.logger.exception("RedisError: falling back to default circuit state")
            return self._fallback_circuit_state

        state = self._fallback_circuit_state
        if state_bytes is not None:
            state = state_bytes.decode("utf-8")
        else:
            # state retrieved from redis was missing, so we re-initialize
            # the circuit breaker state on redis
            self._initialize_redis_state(self._fallback_circuit_state)

        return state

    @state.setter
    def state(self, state: str) -> None:
        """Set the current circuit breaker state to `state`."""
        try:
            self._redis.set(self._namespace("state"), str(state))
        except RedisError:
            self.logger.exception("RedisError")

    def increment_counter(self) -> None:
        """Increase the failure counter by one."""
        try:
            self._redis.incr(self._namespace("fail_counter"))
        except RedisError:
            self.logger.exception("RedisError")

    def reset_counter(self) -> None:
        """Set the failure counter to zero."""
        try:
            self._redis.set(self._namespace("fail_counter"), 0)
        except RedisError:
            self.logger.exception("RedisError")

    def increment_success_counter(self) -> None:
        """Increase the success counter by one."""
        try:
            self._redis.incr(self._namespace("success_counter"))
        except RedisError:
            self.logger.exception("RedisError")

    def reset_success_counter(self) -> None:
        """Set the success counter to zero."""
        try:
            self._redis.set(self._namespace("success_counter"), 0)
        except RedisError:
            self.logger.exception("RedisError")

    @property
    def counter(self) -> int:
        """Return the current value of the failure counter."""
        try:
            value = self._redis.get(self._namespace("fail_counter"))
            if value:
                return int(value)
            return 0
        except RedisError:
            self.logger.exception("RedisError: Assuming no errors")
            return 0

    @property
    def success_counter(self) -> int:
        """Return the current value of the success counter."""
        try:
            value = self._redis.get(self._namespace("success_counter"))
            if value:
                return int(value)
            return 0
        except RedisError:
            self.logger.exception("RedisError: Assuming no successes")
            return 0

    @property
    def opened_at(self) -> datetime | None:
        """Returns a datetime object of the most recent value of when the circuit was opened."""
        try:
            timestamp = self._redis.get(self._namespace("opened_at"))
            if timestamp:
                return datetime(*time.gmtime(int(timestamp))[:6], tzinfo=UTC)
        except RedisError:
            self.logger.exception("RedisError")
        return None

    @opened_at.setter
    def opened_at(self, now: datetime) -> None:
        """Atomically set the most recent value of when the circuit was opened
        to `now`. Stored in redis as a simple integer of unix epoch time.
        To avoid timezone issues between different systems, the passed in
        datetime should be in UTC.
        """
        try:
            key = self._namespace("opened_at")

            if self._cluster_mode:
                current_value = self._redis.get(key)
                next_value = int(calendar.timegm(now.timetuple()))

                if not current_value or next_value > int(current_value):
                    self._redis.set(key, next_value)

            else:

                def set_if_greater(pipe: Pipeline[bytes]) -> None:
                    current_value = cast(bytes, pipe.get(key))
                    next_value = int(calendar.timegm(now.timetuple()))
                    pipe.multi()
                    if not current_value or next_value > int(current_value):
                        pipe.set(key, next_value)

                self._redis.transaction(set_if_greater, key)

        except RedisError:
            self.logger.exception("RedisError")

    def _namespace(self, key: str) -> str:
        name_parts = [self.BASE_NAMESPACE, key]
        if self._namespace_name:
            name_parts.insert(0, self._namespace_name)

        return ":".join(name_parts)


class CircuitBreakerListener:
    """Listener class used to plug code to a ``CircuitBreaker`` instance when certain events happen."""

    def before_call(self, cb: CircuitBreaker, func: Callable[..., T], *args: Any, **kwargs: Any) -> None:
        """This callback function is called before the circuit breaker `cb` calls `fn`."""

    def failure(self, cb: CircuitBreaker, exc: BaseException) -> None:
        """This callback function is called when a function called by the circuit breaker `cb` fails."""

    def success(self, cb: CircuitBreaker) -> None:
        """This callback function is called when a function called by the circuit breaker `cb` succeeds."""

    def state_change(
        self,
        cb: CircuitBreaker,
        old_state: CircuitBreakerState | None,
        new_state: CircuitBreakerState,
    ) -> None:
        """This callback function is called when the state of the circuit breaker `cb` state changes."""


class CircuitBreakerState:
    """Implement the behavior needed by all circuit breaker states."""

    def __init__(self, cb: CircuitBreaker, name: str) -> None:
        """Create a new instance associated with the circuit breaker `cb` and identified by `name`."""
        self._breaker: CircuitBreaker = cb
        self._name: str = name

    @property
    def name(self) -> str:
        """Return a human friendly name that identifies this state."""
        return self._name

    @overload
    def _handle_error(self, exc: BaseException, reraise: Literal[True] = ...) -> NoReturn:
        ...

    @overload
    def _handle_error(self, exc: BaseException, reraise: Literal[False] = ...) -> None:
        ...

    def _handle_error(self, exc: BaseException, reraise: bool = True) -> None:
        """Handle a failed call to the guarded operation."""
        if self._breaker.is_system_error(exc):
            self._breaker._inc_counter()
            for listener in self._breaker.listeners:
                listener.failure(self._breaker, exc)
            self.on_failure(exc)
        else:
            self._handle_success()

        if reraise:
            raise exc

    def _handle_success(self) -> None:
        """Handle a successful call to the guarded operation."""
        self._breaker._state_storage.reset_counter()
        self.on_success()
        for listener in self._breaker.listeners:
            listener.success(self._breaker)

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Calls `func` with the given `args` and `kwargs`, and updates the
        circuit breaker state according to the result.
        """
        ret = None

        self.before_call(func, *args, **kwargs)
        for listener in self._breaker.listeners:
            listener.before_call(self._breaker, func, *args, **kwargs)

        try:
            ret = func(*args, **kwargs)
            if isinstance(ret, types.GeneratorType):
                return self.generator_call(ret)

        except BaseException as e:
            self._handle_error(e)
        else:
            self._handle_success()
        return ret

    def call_async(self, func, *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        """Call async `func` with the given `args` and `kwargs`, and updates the
        circuit breaker state according to the result.

        Return a closure to prevent import errors when using without tornado present
        """

        @gen.coroutine
        def wrapped():  # type: ignore[no-untyped-def]
            ret = None

            self.before_call(func, *args, **kwargs)
            for listener in self._breaker.listeners:
                listener.before_call(self._breaker, func, *args, **kwargs)

            try:
                ret = yield func(*args, **kwargs)
                if isinstance(ret, types.GeneratorType):
                    raise gen.Return(self.generator_call(ret))

            except BaseException as e:
                self._handle_error(e)
            else:
                self._handle_success()
            raise gen.Return(ret)

        return wrapped()

    def generator_call(self, wrapped_generator):  # type: ignore[no-untyped-def]
        try:
            value = yield next(wrapped_generator)
            while True:
                value = yield wrapped_generator.send(value)
        except StopIteration:
            self._handle_success()
            return
        except BaseException as e:
            self._handle_error(e, reraise=False)
            wrapped_generator.throw(e)

    def before_call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """Override this method to be notified before a call to the guarded operation is attempted."""

    def on_success(self) -> None:
        """Override this method to be notified when a call to the guarded operation succeeds."""

    def on_failure(self, exc: BaseException) -> None:
        """Override this method to be notified when a call to the guarded operation fails."""


class CircuitClosedState(CircuitBreakerState):
    """In the normal "closed" state, the circuit breaker executes operations as
    usual. If the call succeeds, nothing happens. If it fails, however, the
    circuit breaker makes a note of the failure.

    Once the number of failures exceeds a threshold, the circuit breaker trips
    and "opens" the circuit.
    """

    def __init__(
        self,
        cb: CircuitBreaker,
        prev_state: CircuitBreakerState | None = None,
        notify: bool = False,
    ) -> None:
        """Move the given circuit breaker `cb` to the "closed" state."""
        super().__init__(cb, STATE_CLOSED)
        if notify:
            # We only reset the counter if notify is True, otherwise the CircuitBreaker
            # will lose it's failure count due to a second CircuitBreaker being created
            # using the same _state_storage object, or if the _state_storage objects
            # share a central source of truth (as would be the case with the redis
            # storage).
            self._breaker._state_storage.reset_counter()
            for listener in self._breaker.listeners:
                listener.state_change(self._breaker, prev_state, self)

    def on_failure(self, exc: BaseException) -> None:
        """Move the circuit breaker to the "open" state once the failures threshold is reached."""
        if self._breaker._state_storage.counter >= self._breaker.fail_max:
            throw_new_error = self._breaker.open()

            if throw_new_error:
                error_msg = "Failures threshold reached, circuit breaker opened"
                raise CircuitBreakerError(error_msg).with_traceback(sys.exc_info()[2])
            raise exc


class CircuitOpenState(CircuitBreakerState):
    """When the circuit is "open", calls to the circuit breaker fail immediately,
    without any attempt to execute the real operation. This is indicated by the
    ``CircuitBreakerError`` exception.

    After a suitable amount of time, the circuit breaker decides that the
    operation has a chance of succeeding, so it goes into the "half-open" state.
    """

    def __init__(
        self,
        cb: CircuitBreaker,
        prev_state: CircuitBreakerState | None = None,
        notify: bool = False,
    ) -> None:
        """Move the given circuit breaker `cb` to the "open" state."""
        super().__init__(cb, STATE_OPEN)
        if notify:
            # Reset success counter when opening the circuit
            self._breaker._state_storage.reset_success_counter()
            for listener in self._breaker.listeners:
                listener.state_change(self._breaker, prev_state, self)

    def before_call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """After the timeout elapses, move the circuit breaker to the "half-open"
        state; otherwise, raises ``CircuitBreakerError`` without any attempt
        to execute the real operation.
        """
        timeout = timedelta(seconds=self._breaker.reset_timeout)
        opened_at = self._breaker._state_storage.opened_at
        if opened_at and datetime.now(UTC) < opened_at + timeout:
            error_msg = "Timeout not elapsed yet, circuit breaker still open"
            raise CircuitBreakerError(error_msg)
        self._breaker.half_open()
        return self._breaker.call(func, *args, **kwargs)

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Delegate the call to before_call, if the time out is not elapsed it will throw an exception, otherwise we get
        the results from the call performed after the state is switch to half-open.
        """
        return self.before_call(func, *args, **kwargs)


class CircuitHalfOpenState(CircuitBreakerState):
    """In the "half-open" state, the next call to the circuit breaker is allowed
    to execute the dangerous operation. Should the call succeed, the circuit
    breaker resets and returns to the "closed" state. If this trial call fails,
    however, the circuit breaker returns to the "open" state until another
    timeout elapses.
    """

    def __init__(
        self,
        cb: CircuitBreaker,
        prev_state: CircuitBreakerState | None,
        notify: bool = False,
    ) -> None:
        """Move the given circuit breaker `cb` to the "half-open" state."""
        super().__init__(cb, STATE_HALF_OPEN)
        if notify:
            # Reset success counter when entering half-open state
            self._breaker._state_storage.reset_success_counter()
            for listener in self._breaker._listeners:
                listener.state_change(self._breaker, prev_state, self)

    def on_failure(self, exc: BaseException) -> NoReturn:
        """Opens the circuit breaker."""
        throw_new_error = self._breaker.open()

        if throw_new_error:
            error_msg = "Trial call failed, circuit breaker opened"
            raise CircuitBreakerError(error_msg).with_traceback(sys.exc_info()[2])
        raise exc

    def on_success(self) -> None:
        """Increment success counter and close the circuit breaker if threshold is reached."""
        self._breaker._state_storage.increment_success_counter()

        if self._breaker._state_storage.success_counter >= self._breaker.success_threshold:
            self._breaker.close()


class CircuitBreakerError(Exception):
    """When calls to a service fails because the circuit is open, this error is
    raised to allow the caller to handle this type of exception differently.
    """

