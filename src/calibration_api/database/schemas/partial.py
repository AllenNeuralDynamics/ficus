from pydantic import BaseModel, create_model
from typing import Any, List, Optional, Type
from pydantic.fields import FieldInfo
from copy import deepcopy


def partial_model(model: Type[BaseModel], required: List[str] = []) -> Type[BaseModel]:
    """Returns pydantic model based on model given but the fields are all optional, 
    unless the field is listed in required list

    This is used for patch requests since not all fields will be required. 
    However, all fields would be required on post requests.

    Args:
        model (Type[BaseModel]): pydantic model
        required (Optional[list], optional): list of fields to leave as required. Defaults to ().
    """
    def make_field_optional(field: FieldInfo, default: Any = None) -> Any:
        new = deepcopy(field)
        new.default = default
        new.annotation = Optional[field.annotation]  # type: ignore
        return new.annotation, new
    return create_model(
        f'Partial{model.__name__}',
        __base__=model,
        __module__=model.__module__,
        **{
            field_name: make_field_optional(field_info)
            for field_name, field_info in model.model_fields.items() 
            if field_name not in required
        }
    )
