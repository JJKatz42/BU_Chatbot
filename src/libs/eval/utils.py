import enum
import json
import os
from datetime import datetime

import pydantic

import src.libs.logging as logging

logger = logging.getLogger(__name__)


def is_readable_directory(dir_path):
    """
    Check if the directory at dir_path is readable.
    """
    return os.path.isdir(dir_path) and os.access(dir_path, os.R_OK)


def is_readable_file(file_path):
    """
    Check if the file at file_path is readable.
    """
    if file_path is None:
        return False

    if not os.path.exists(file_path):
        return False

    # Try opening the file to check if it's readable
    try:
        with open(file_path, 'r') as file:
            return True
    except IOError:
        return False


def get_current_date() -> str:
    """
    Returns the current date in the "YYYY/MM/DD" format.

    Returns:
        str: The current date.
    """

    # Get the current date
    current_date = datetime.now()

    # Format the date to "YYYY/MM/DD" and return
    return current_date.strftime('%Y/%m/%d')


def _custom_json_encoder(obj):
    if isinstance(obj, pydantic.BaseModel):
        return obj.dict()
    elif isinstance(obj, enum.Enum):
        return obj.value
    else:
        return str(obj)


def save_object_to_json_file(object, filename):
    """
    Save a Python object (supported by json module) to a file in JSON format.

    Parameters:
    - object: The Python object to save.
    - filename (str): The path and name of the file to which the data will be saved.

    The function handles various exceptions including file not found, permission errors,
    and JSON encoding errors. It logs errors using a logger.
    """
    try:
        with open(filename, 'w') as file:
            json.dump(object, file, default=_custom_json_encoder, indent=4)
    except FileNotFoundError:
        logger.error("Error: File not found")
        raise
    except PermissionError:
        logger.error("Error: Permission denied to open the file")
        raise
    except IOError as e:
        logger.error(f"I/O error occurred: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error in encoding JSON: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise


def extract_file_details(file_path):
    """
    Extract directory, file name without extension, and file extension from a given file path.

    Parameters:
    - file_path (str): The path to the file.

    Returns:
    - tuple: (directory, file_name_without_extension, file_extension)
    """

    # Extract directory and file name + extension
    directory, filename_with_ext = os.path.split(file_path)

    # Split file name and extension
    file_name_without_extension, file_extension = os.path.splitext(filename_with_ext)

    return directory, file_name_without_extension, file_extension


def has_overlap(array1, array2):
    """
    This function checks if two Python arrays have any overlap.

    Args:
      array1: The first array.
      array2: The second array.

    Returns:
      True if the arrays have any overlap, False otherwise.

    Example:
      >>> has_overlap([1, 2, 3, 4, 5], [3, 4, 5, 6, 7])
      True
    """

    return any(element in array2 for element in array1)