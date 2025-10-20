import os
import json
import csv
import glob
from datetime import datetime


# Printing and progress
def jprint(data):
    print(json.dumps(data, indent=2))


def print_percentage(progress, total):
    progress = min(progress, total)
    percentage = round(progress * 100 / total, 2)
    print(f"\r{percentage}% done  ", end="", flush=True)
    if progress == total:
        print()
    return progress + 1


# File management
def ensure_path_exists(path, mute=True):
    """
    Check if a directory exists at 'path'. If not, create it.
    """
    if not os.path.exists(path):
        os.makedirs(path)
        if not mute:
            print(f"Created directory: {path}")


def check_file_existence(path):
    return os.path.exists(path)


def delete_file(file_path, debug=False):
    """
    Deletes the specified file.

    Parameters:
    file_path (str): Path to the file to delete.

    Returns:
    None
    """
    try:
        os.remove(file_path)  # Attempt to remove the file
        if debug:
            print(f"{file_path} has been deleted.")
    except FileNotFoundError:
        if debug:
            print(f"{file_path} does not exist.")
    except PermissionError:
        if debug:
            print(f"Permission denied: Unable to delete {file_path}.")
    except Exception as e:
        if debug:
            print(f"An error occurred: {e}")


def find_file_type(directory, file_type):
    # Search for all CSV files in the specified directory
    files = glob.glob(os.path.join(directory, f"*.{file_type}"))
    # Return the list of CSV file paths
    return files


# JSON
def json_import(filename, mute=True):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            if not mute:
                print(f"{filename} loaded.")
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []  # Handle missing or corrupted file


def json_export(data, filename, mute=True):
    file_path = f"{filename}"
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            if not mute:
                print("Export successful.")
    except Exception as e:
        print(f"Error during JSON export : {e}")


# CSV
def csv_import(file_path):
    # Ensure the file exists
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    with open(file_path, "r", encoding="utf-8") as original_file:
        reader = csv.DictReader(
            original_file
        )  # Use DictReader to use the first row as headers
        data = [
            row for row in reader
        ]  # Convert the DictReader object to a list of dictionaries

    return data


def csv_export(data, filename, date=False, mute=True, look_for_keys=False, keys=None):

    if filename.endswith(".csv"):
        filename = filename[:-4]

    formatted_date = ""
    if date:
        current_date = datetime.now()
        formatted_date = "_" + current_date.strftime("%Y_%m_%d")

    # Format the file
    csv_file = filename + formatted_date + ".csv"

    # Create the directory if it doesn't exist
    folder = os.path.dirname(csv_file)
    if folder:
        os.makedirs(folder, exist_ok=True)

    if keys:
        csv_headers = keys
    else:
        if look_for_keys:
            csv_headers = list_of_dict_get_keys(data)
        else:
            csv_headers = data[0].keys()

    # Open the CSV file in write mode
    with open(csv_file, mode="w", encoding="utf-8", newline="") as file:
        # Create a DictWriter object
        writer = csv.DictWriter(file, fieldnames=csv_headers)

        # Write the headers to the CSV file
        writer.writeheader()

        # Write the data rows to the CSV file
        writer.writerows(data)

    if not mute:
        print(f"Data has been successfully written to {csv_file}")

    return csv_file


# TXT
def txt_import(file_path):
    # Reading the entire content of the file
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            return content
    except FileNotFoundError:
        print("The file does not exist. Please check the file path and try again.")
        return None


def txt_overwrite(text, file_path):
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(text)


# Variable management
def remove_trailing_spaces(text):
    if text.endswith(" "):
        text = text.rstrip()
    return text


def list_join(list, separator="|"):
    result_string = separator.join(str(item) for item in list)
    return result_string


def reorder_dict(original_dict, key_order, default_value=None, replace_blank=True):
    result_dict = {key: original_dict.get(key, None) for key in key_order}
    if replace_blank:
        for k, v in result_dict.items():
            try:
                if len(v) == 0:
                    v = default_value
            except:
                pass
    return result_dict


def count_occurences_list(data_list):
    result_dict = {item: 0 for item in list(set(data_list))}
    for item in data_list:
        result_dict[item] += 1
    return result_dict


def find_index_of_value(value, key, list_of_dicts):
    for index, d in enumerate(list_of_dicts):
        if d.get(key) == value:
            return index
    return None


def extract_identifier(url):
    url_clean = url.split("?")[0]
    last_char = len(url_clean) - 1
    if url_clean[last_char] == "/":
        url_clean = url_clean[:last_char]
    identifier = url_clean.split("/")[-1]
    return identifier


def list_of_dict_get_keys(data):
    if data is None:
        raise ValueError("Expected a list of dicts, got None.")
    # If it's a generator/iterator, materialize it once
    if not hasattr(data, "__len__") or not hasattr(data, "__getitem__"):
        data = list(data)

    if len(data) == 0:
        raise ValueError("No rows to export (empty list).")

    keys = set()
    for i, row in enumerate(data):
        if not isinstance(row, dict):
            raise TypeError(
                f"Row {i} is {type(row).__name__}, expected dict. " f"Value: {row!r}"
            )
        keys.update(row.keys())
    return list(keys)


def deduplicate_list_of_dicts(data):
    if len(data) == 0:
        return data
    keys_order = list_of_dict_get_keys(data)
    cleaned_data = []
    data_set = set()

    for item in data:
        data_set.add(json.dumps(item, sort_keys=True))

    data_list = list(data_set)

    for item in data_list:
        item_dict = json.loads(item)
        cleaned_data.append(reorder_dict(item_dict, keys_order))

    return cleaned_data
