"""XSD validator for Pohoda XML documents.

Validates generated XML against Pohoda XSD schemas if available.
Falls back to basic well-formedness check if XSD files are not present.
"""

import logging
from pathlib import Path

from lxml import etree

logger = logging.getLogger(__name__)


class XSDValidator:
    """Validator for Pohoda XML documents against XSD schemas.

    Attempts to load XSD schemas from backend/xsd/ directory.
    If schemas are not available, performs basic XML well-formedness validation.
    """

    def __init__(self, xsd_dir: Path | None = None) -> None:
        """Initialize XSD validator.

        Args:
            xsd_dir: Optional path to directory containing XSD schema files.
                    Defaults to backend/xsd/ relative to project root.
        """
        if xsd_dir is None:
            # Default to backend/xsd/ directory
            backend_dir = Path(__file__).parent.parent.parent.parent
            xsd_dir = backend_dir / "xsd"

        self.xsd_dir = xsd_dir
        self.schema: etree.XMLSchema | None = None
        self._load_schema()

    def _load_schema(self) -> None:
        """Load XSD schema from disk if available.

        Looks for data.xsd (main schema) in xsd_dir.
        Logs warning and sets schema to None if not found.
        """
        if not self.xsd_dir.exists():
            logger.warning(
                f"XSD directory not found: {self.xsd_dir}. "
                "XML validation will use basic well-formedness check only."
            )
            return

        # Main schema file for dataPack
        main_schema_file = self.xsd_dir / "data.xsd"

        if not main_schema_file.exists():
            logger.warning(
                f"Main XSD schema not found: {main_schema_file}. "
                "XML validation will use basic well-formedness check only."
            )
            return

        try:
            # Parse XSD schema
            with main_schema_file.open("rb") as f:
                schema_doc = etree.parse(f)
                self.schema = etree.XMLSchema(schema_doc)

            logger.info(f"Loaded XSD schema from: {main_schema_file}")

        except etree.XMLSchemaParseError as e:
            logger.error(f"Failed to parse XSD schema: {e}")
            self.schema = None
        except Exception as e:
            logger.error(f"Unexpected error loading XSD schema: {e}")
            self.schema = None

    def validate(self, xml_bytes: bytes) -> tuple[bool, list[str]]:
        """Validate XML document against XSD schema or check well-formedness.

        Args:
            xml_bytes: XML document as bytes to validate.

        Returns:
            tuple[bool, list[str]]: Tuple of (is_valid, error_messages).
                                   is_valid is True if validation passed.
                                   error_messages contains list of validation errors.
        """
        errors: list[str] = []

        try:
            # Parse XML document
            xml_doc = etree.fromstring(xml_bytes)

        except etree.XMLSyntaxError as e:
            # Not well-formed XML
            errors.append(f"XML syntax error: {e}")
            return (False, errors)
        except Exception as e:
            errors.append(f"Failed to parse XML: {e}")
            return (False, errors)

        # If schema is available, validate against it
        if self.schema is not None:
            try:
                is_valid = self.schema.validate(xml_doc)

                if not is_valid:
                    # Collect all validation errors
                    for error in self.schema.error_log:
                        errors.append(f"Line {error.line}: {error.message}")
                    return (False, errors)

                # Validation passed
                return (True, [])

            except Exception as e:
                errors.append(f"Schema validation error: {e}")
                return (False, errors)

        else:
            # No schema available - XML is well-formed, consider valid
            logger.debug("No XSD schema loaded. XML is well-formed - considering valid.")
            return (True, [])

    def validate_string(
        self,
        xml_string: str,
        encoding: str = "Windows-1250",
    ) -> tuple[bool, list[str]]:
        """Validate XML string (convenience method).

        Args:
            xml_string: XML document as string.
            encoding: Encoding of the string (default: Windows-1250).

        Returns:
            tuple[bool, list[str]]: Tuple of (is_valid, error_messages).
        """
        xml_bytes = xml_string.encode(encoding)
        return self.validate(xml_bytes)
