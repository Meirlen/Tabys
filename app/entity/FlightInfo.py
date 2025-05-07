class FlightInfo:
    """
    A class to represent a user's trip details.

    Attributes:
        passenger_count (int): The number of passengers.
        date (str): The date of the trip.
        from_city (str): The departure city.
        to_city (str): The destination city.
    """

    def __init__(self, passenger_count: int, date: str, from_city: str, to_city: str, lang: str):
        """
        Initializes the TripInfo object with the provided details.

        Args:
            passenger_count (int): The number of passengers.
            date (str): The date of the trip.
            from_city (str): The departure city.
            to_city (str): The destination city.
        """
        self.passenger_count = passenger_count
        self.date = date
        self.from_city = from_city
        self.to_city = to_city
        self.lang = lang

    def __repr__(self):
        """
        Returns a string representation of the TripInfo object.

        Returns:
            str: A formatted string showing the trip details.
        """
        return f"TripInfo(passenger_count={self.passenger_count}, date={self.date}, from_city={self.from_city}, to_city={self.to_city})"

    def format_trip_info(self):
        """
        Formats the trip information into a string.

        Returns:
            str: A formatted string with the trip details.
        """
        return f"Passengers: {self.passenger_count}, Date: {self.date}, From: {self.from_city}, To: {self.to_city}"


def create_trip_summary(trips):
    """
    Creates a summary of trip information.

    Args:
        trips (list): A list of TripInfo objects.

    Returns:
        str: A formatted string with all trip details, each on a new line.
    """
    return '\n\n'.join(trip.format_trip_info() for trip in trips)