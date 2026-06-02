"""S3 event envelope, as delivered to SQS by an S3 bucket notification.

Reference: https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-content-structure.html

Pydantic with `extra="allow"` so any future fields S3 / LocalStack add
won't break our parser.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class S3Bucket(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str


class S3Object(BaseModel):
    model_config = ConfigDict(extra="allow")
    key: str
    size: int = 0


class S3EventDetail(BaseModel):
    model_config = ConfigDict(extra="allow")
    bucket: S3Bucket
    object: S3Object


class S3EventRecord(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    event_version: str | None = Field(default=None, alias="eventVersion")
    event_source: str = Field(alias="eventSource")
    event_name: str = Field(alias="eventName")
    event_time: datetime | None = Field(default=None, alias="eventTime")
    s3: S3EventDetail


class S3EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    records: list[S3EventRecord] = Field(alias="Records")
