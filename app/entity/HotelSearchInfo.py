class HotelSearchInfo:
    """
    A class to represent a user's hotel search details.

    Attributes:
        guest_count (int): The number of guests.
        from_date (str): The check-in date.
        to_date (str): The check-out date.
        city (str): The city where the hotel is located.
    """

    def __init__(self, guest_count: int, from_date: str, to_date: str, city: str):
        """
        Initializes the HotelSearchInfo object with the provided details.

        Args:
            guest_count (int): The number of guests.
            from_date (str): The check-in date.
            to_date (str): The check-out date.
            city (str): The city where the hotel is located.
        """
        self.guest_count = guest_count
        self.from_date = from_date
        self.to_date = to_date
        self.city = city

    def __repr__(self):
        """
        Returns a string representation of the HotelSearchInfo object.

        Returns:
            str: A formatted string showing the hotel search details.
        """
        return f"HotelSearchInfo(guest_count={self.guest_count}, from_date={self.from_date}, to_date={self.to_date}, city={self.city})"

    def format_hotel_info(self):
        """
        Formats the hotel search information into a string.

        Returns:
            str: A formatted string with the hotel search details.
        """
        return f"Guests: {self.guest_count}, Check-in: {self.from_date}, Check-out: {self.to_date}, City: {self.city}"


def create_hotel_summary(hotels):
    """
    Creates a summary of hotel search information.

    Args:
        hotels (list): A list of HotelSearchInfo objects.

    Returns:
        str: A formatted string with all hotel details, each on a new line.
    """
    return '\n\n'.join(hotel.format_hotel_info() for hotel in hotels)
