from src.operators.validator import SampleValidator
from src.operators.image_loader import ImageLoader
from src.operators.resolution_filter import ResolutionFilter
from src.operators.blur_filter import BlurFilter
from src.operators.clip_alignment import CLIPAlignmentOperator


def build_operators(config: dict):

    operators = []

    operator_configs = config["pipeline"]["operators"]

    for operator_config in operator_configs:

        if not operator_config.get("enabled", True):
            continue

        name = operator_config["name"]

        params = operator_config.get(
            "params",
            {}
        )

        if name == "validator":

            operator = SampleValidator()

        elif name == "image_loader":

            operator = ImageLoader()

        elif name == "resolution_filter":

            operator = ResolutionFilter(
                **params
            )

        elif name == "blur_filter":

            operator = BlurFilter(
                **params
            )

        elif name == "clip_alignment":

            operator = CLIPAlignmentOperator(
                **params
            )

        else:

            raise ValueError(
                f"Unknown operator: {name}"
            )

        operators.append(operator)

    return operators

        