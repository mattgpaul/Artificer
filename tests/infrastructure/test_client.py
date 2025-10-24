"""Unit tests for Client - Abstract Base Class.

Tests cover abstract class enforcement and that concrete implementations
properly inherit from the Client ABC.
"""

from abc import ABC, ABCMeta, abstractmethod

from infrastructure.client import Client


class ConcreteClient(Client):
    """Concrete implementation for testing abstract Client."""

    pass


class TestClientAbstractClass:
    """Test Client abstract base class."""

    def test_client_is_abstract(self):
        """Test Client is an abstract base class."""
        assert isinstance(Client, ABCMeta)

    def test_client_can_be_subclassed(self):
        """Test Client can be subclassed."""
        client = ConcreteClient()

        assert isinstance(client, Client)
        assert isinstance(client, ABC)

    def test_client_has_no_abstract_methods(self):
        """Test Client has no required abstract methods in base."""
        # Client itself doesn't define abstract methods, just serves as a marker
        # Subclasses can instantiate without implementing anything
        client = ConcreteClient()
        assert client is not None

    def test_multiple_inheritance_levels(self):
        """Test multiple levels of inheritance from Client."""

        class IntermediateClient(Client):
            pass

        class FinalClient(IntermediateClient):
            pass

        client = FinalClient()
        assert isinstance(client, Client)
        assert isinstance(client, IntermediateClient)

    def test_client_as_interface_marker(self):
        """Test Client serves as an interface marker for type checking."""
        client = ConcreteClient()

        # Should be recognized as a Client type
        assert isinstance(client, Client)

        # Type checking function
        def accepts_client(c: Client):
            return True

        assert accepts_client(client)


class TestClientInheritance:
    """Test Client inheritance patterns used in codebase."""

    def test_redis_client_pattern(self):
        """Test Redis client inheritance pattern."""

        class MockRedisClient(Client):
            def __init__(self):
                super().__init__()
                self.namespace = "test"

            def get(self, key):
                return f"value_for_{key}"

        client = MockRedisClient()
        assert isinstance(client, Client)
        assert client.get("test_key") == "value_for_test_key"

    def test_influxdb_client_pattern(self):
        """Test InfluxDB client inheritance pattern."""

        class MockInfluxDBClient(Client):
            def __init__(self, database):
                self.database = database

            @abstractmethod
            def write(self):
                pass

            @abstractmethod
            def query(self):
                pass

        class ConcreteInfluxClient(MockInfluxDBClient):
            def write(self):
                return "writing"

            def query(self):
                return "querying"

        client = ConcreteInfluxClient(database="test_db")
        assert isinstance(client, Client)
        assert client.database == "test_db"
        assert client.write() == "writing"
        assert client.query() == "querying"

    def test_client_with_abstract_methods(self):
        """Test Client subclass with abstract methods."""

        class AbstractClient(Client):
            @abstractmethod
            def connect(self):
                pass

            @abstractmethod
            def disconnect(self):
                pass

        class ImplementedClient(AbstractClient):
            def connect(self):
                return "connected"

            def disconnect(self):
                return "disconnected"

        client = ImplementedClient()
        assert isinstance(client, Client)
        assert client.connect() == "connected"
        assert client.disconnect() == "disconnected"


class TestClientEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_client_implementation(self):
        """Test simplest possible Client implementation."""

        class MinimalClient(Client):
            pass

        client = MinimalClient()
        assert client is not None
        assert isinstance(client, Client)

    def test_client_with_state(self):
        """Test Client with internal state."""

        class StatefulClient(Client):
            def __init__(self):
                super().__init__()
                self.connected = False
                self.data = {}

            def connect(self):
                self.connected = True

            def store(self, key, value):
                self.data[key] = value

            def retrieve(self, key):
                return self.data.get(key)

        client = StatefulClient()
        assert not client.connected

        client.connect()
        assert client.connected

        client.store("test", "value")
        assert client.retrieve("test") == "value"

    def test_client_inheritance_with_init(self):
        """Test Client inheritance properly calls super().__init__()."""
        init_calls = []

        class BaseClient(Client):
            def __init__(self):
                super().__init__()
                init_calls.append("BaseClient")

        class DerivedClient(BaseClient):
            def __init__(self):
                super().__init__()
                init_calls.append("DerivedClient")

        init_calls.clear()
        DerivedClient()

        assert "BaseClient" in init_calls
        assert "DerivedClient" in init_calls

    def test_client_multiple_concrete_classes(self):
        """Test multiple concrete Client implementations."""

        class ClientA(Client):
            def method_a(self):
                return "A"

        class ClientB(Client):
            def method_b(self):
                return "B"

        client_a = ClientA()
        client_b = ClientB()

        assert isinstance(client_a, Client)
        assert isinstance(client_b, Client)
        assert client_a.method_a() == "A"
        assert client_b.method_b() == "B"

    def test_client_with_class_methods(self):
        """Test Client with class and static methods."""

        class UtilityClient(Client):
            instances = 0

            def __init__(self):
                super().__init__()
                UtilityClient.instances += 1

            @classmethod
            def get_instance_count(cls):
                return cls.instances

            @staticmethod
            def helper_method():
                return "helper"

        UtilityClient.instances = 0  # Reset

        UtilityClient()
        UtilityClient()

        assert UtilityClient.get_instance_count() == 2
        assert UtilityClient.helper_method() == "helper"

    def test_client_with_properties(self):
        """Test Client with property decorators."""

        class PropertyClient(Client):
            def __init__(self):
                super().__init__()
                self._value = 0

            @property
            def value(self):
                return self._value

            @value.setter
            def value(self, val):
                self._value = val

        client = PropertyClient()
        assert client.value == 0

        client.value = 42
        assert client.value == 42


class TestClientTypeChecking:
    """Test type checking and isinstance behavior."""

    def test_isinstance_check(self):
        """Test isinstance works correctly with Client."""
        client = ConcreteClient()

        assert isinstance(client, Client)
        assert isinstance(client, ABC)
        assert isinstance(client, object)

    def test_issubclass_check(self):
        """Test issubclass works correctly with Client."""
        assert issubclass(ConcreteClient, Client)
        assert issubclass(ConcreteClient, ABC)
        assert issubclass(Client, ABC)

    def test_type_check(self):
        """Test type() returns correct type."""
        client = ConcreteClient()

        assert type(client).__name__ == "ConcreteClient"
        assert issubclass(type(client), Client)

    def test_client_in_collection(self):
        """Test Client instances work correctly in collections."""

        class ClientType1(Client):
            def get_type(self):
                return 1

        class ClientType2(Client):
            def get_type(self):
                return 2

        clients = [ClientType1(), ClientType2(), ClientType1()]

        assert len(clients) == 3
        assert all(isinstance(c, Client) for c in clients)

    def test_client_polymorphism(self):
        """Test polymorphism with Client base class."""

        class Reader(Client):
            def process(self):
                return "reading"

        class Writer(Client):
            def process(self):
                return "writing"

        def execute_client(client: Client):
            return client.process()

        reader = Reader()
        writer = Writer()

        assert execute_client(reader) == "reading"
        assert execute_client(writer) == "writing"
