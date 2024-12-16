from typing import List, Union, Optional
from datetime import datetime
import otter

class TransientRead(otter.schema.OtterSchema):
    _id: int
    _key: int
