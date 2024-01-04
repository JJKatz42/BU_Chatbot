import enum
import json
import collections
import pydantic
from datetime import datetime

from pydantic import BaseModel  # pylint: disable=no-member

from src.libs.logging import logging


logger = logging.getLogger(__name__)


class EvaluationTag(enum.Enum):
    REQ_CLARITY_AMBIGUOUS = "REQ_CLARITY_AMBIGUOUS"
    REQ_LANGUAGE_MISSPELLING = "REQ_LANGUAGE_MISSPELLING"
    REQ_LANGUAGE_BAD_GRAMMAR = "REQ_LANGUAGE_BAD_GRAMMAR"
    REQ_REQUIRES_CONTEXT = "REQ_REQUIRES_CONTEXT"

    RSP_NEEDS_METADATA = "RSP_NEEDS_METADATA"
    RSP_USED_IN_BOT_FEATURES = "RSP_USED_IN_BOT_FEATURES"

    RES_EXPECT_SIMPLE_FACT = "RES_EXPECT_SIMPLE_FACT"
    RES_EXPECT_COMPLEX_FACT = "RES_EXPECT_COMPLEX_FACT"
    RES_EXPECT_LIST_OF_SIMPLE_FACTS = "RES_EXPECT_LIST_OF_SIMPLE_FACTS"
    RES_EXPECT_LIST_OF_COMPLEX_FACTS = "RES_EXPECT_LIST_OF_COMPLEX_FACTS"

    RES_EXPECT_FACT_BASED = "RES_EXPECT_FACT_BASED"
    RES_EXPECT_FACT_SYNTHESIS_BASED = "RES_EXPECT_FACT_SYNTHESIS_BASED"
    RES_EXPECT_CREATIVE = "RES_EXPECT_FACT_SYNTHESIS_BASED"

    SUBJECT_COURSES = "SUBJECT_COURSES"
    SUBJECT_ADMISSIONS = "SUBJECT_ADMISSIONS"

    RSP_EXPECT_NUMBER = "RSP_EXPECT_NUMBER"
    RSP_EXPECT_PARAGRAPH = "RSP_EXPECT_PARAGRAPH"
    RSP_EXPECT_ESSAY = "RSP_EXPECT_ESSAY"
    RSP_EXPECT_INSTRUCTIONS = "RSP_EXPECT_INSTRUCTIONS"
    RSP_EXPECT_LINK = "RSP_EXPECT_LINK"

    # Software features

    RSP_USES_UNCONTESTED_FACTS = "RSP_USES_UNCONTESTED_FACTS"
    RSP_USES_CONFLICTING_FACTS_SINGLE_SOURCE = "RSP_USES_CONFLICTING_FACTS_SINGLE_SOURCE"
    RSP_USES_CONFLICTING_FACTS_MULTIPLE_SOURCES = "RSP_USES_CONFLICTING_FACTS_MULTIPLE_SOURCES"


class EvaluationTestMetadata(BaseModel):
    related_kips: list[str]
    related_tests: list[str]
    date_added: str
    test_id: str
    classification_tags: list[EvaluationTag]

    @pydantic.validator("date_added")
    def validate_date(cls, v):
        try:
            # try to parse the date string
            return datetime.strptime(v, "%Y/%m/%d").date()
        except ValueError:
            # raise a ValueError if the input is not in the right format
            raise ValueError("Incorrect data format, should be YYYY/MM/DD")


class EvaluationTestDefinition(BaseModel):
    request: str
    enable: bool
    expected_response: str
    inverse_test: bool


class EvaluationTest(BaseModel):
    metadata: EvaluationTestMetadata
    definition: EvaluationTestDefinition


class EvaluationTestList(BaseModel):
    __root__: list[EvaluationTest]

    # validate uniqueness of test ids
    @pydantic.validator("__root__", each_item=False)
    def validate_unique_ids(cls, __root__):
        counter = collections.Counter([test.metadata.test_id for test in __root__])
        # Iterate over the items in the Counter object. Each item in the Counter object is a tuple,
        # The first element is an item from list and the second element is the count of that item.
        non_unique_test_ids = [item for item, count in counter.items() if count > 1]

        if len(non_unique_test_ids) > 0:
            logger.warning(f"Non-unique test ids in the test file: {non_unique_test_ids}")
            raise ValueError('test IDs must be unique')

class EvaluationTestSchema:
    """Interface Class to the test schema."""

    @staticmethod
    def validate_test_file(file_in: str) -> bool:
        """Validate JSON test file. log useful debug information if validation fails

        Args:
            file_in: Test file to validate

        Returns:
            True if file passed validation False if failed validation
        """
        with open(file_in, "r") as f:
            data = json.load(f)

        try:
            tests = EvaluationTestList.parse_obj(data)
        except pydantic.ValidationError as e:
            logger.error(e)
            return False
        except Exception as e:
            logger.error(f"Error occurred while reading test file: {str(e)}")
            return False

        return True

    @staticmethod
    def write_schema_to_file(file_path: str) -> None:
        """
        Writes the JSON schema of a Pydantic test model to a file.

        Args:
            file_path (str): The path to the file where the schema will be saved.

        Returns:
            None
        """
        try:
            # Generate the JSON schema
            schema = EvaluationTestList.schema_json(indent=4)

            # Save the schema to the file
            with open(file_path, 'w') as f:
                f.write(schema)

        except Exception as e:
            logger.error(f"Error occurred while writing schema to file: {str(e)}")


if __name__ == "__main__":
    # Generate and save the JSON schema
    try:
        EvaluationTestSchema.write_schema_to_file('schema.json')
    except Exception as e:
        logger.error(f"Error occurred while generating schema: {str(e)}")

    logger.info("wrote schema to file \"schema.json\".")

    # Read and validate the JSON file
    if EvaluationTestSchema.validate_test_file('../defintions/test_example.json'):
        logger.info("validate_test_file success!")
    else:
        logger.error("validate_test_file failure!")