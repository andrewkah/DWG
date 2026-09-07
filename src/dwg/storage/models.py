from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, JSON, UniqueConstraint, Index, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import UUID
import uuid

class Base(DeclarativeBase):
    pass

class OrganizationModel(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"OrganizationModel(id={self.id}, name={self.name}, created_at={self.created_at}, updated_at={self.updated_at})"
    
class WorkflowModel(Base):
    __tablename__ = "workflows"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    draft_definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint(
                    "organization_id", 
                    "slug", 
                    name="uq_org_workflow_slug "
                ),
        Index("idx_workflows_org", "organization_id"),
    )
    
    def __repr__(self):
        return f"WorkflowModel(id={self.id}, name={self.name}, organization_id={self.organization_id}, created_at={self.created_at}, updated_at={self.updated_at})"

class ApiKeysModel(Base):
    __tablename__ = "api_keys"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[str] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        Index("idx_api_keys_org", "organization_id"),
    )
    
    def __repr__(self):
        return f"ApiKeysModel(id={self.id}, workflow_id={self.workflow_id}, api_key={self.api_key}, created_at={self.created_at}, revoked_at={self.revoked_at})"


class WorkflowVersionsModel(Base):
    __tablename__ = "workflow_versions"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    published_by: Mapped[str] = mapped_column(String(255), nullable=False)
    published_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint(
            "workflow_id", 
            "version_number", 
            name="uq_workflow_version"
        ),
    )
    
    def __repr__(self):
        return f"Workflow Versions(id={self.id}, workflow_id={self.workflow_id}, version_number={self.version_number}, definition={self.definition})"


class ProviderProfilesModel(Base):
    __tablename__ = "provider_profiles"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    max_screen_length: Mapped[int] = mapped_column(Integer, nullable=False, default=160)
    session_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=180)
    protocol_features: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: {})
    
    def __repr__(self):
        return f"Provider Profiles(id={self.id}, name={self.name}, max screen length={self.max_screen_length}, protocal features={self.protocol_features})"

class ChannelBindingsModel(Base):
    __tablename__ = "channel_bindings"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    workflow_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_versions.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    routing_identifier: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("provider_profiles.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint(
            "routing_identifier",
            "channel", 
            name="uq_channel_routing"
        ),
    )
    
    def __repr__(self):
            return f"Channel Bindings (id={self.id}, organization={self.organization_id}, workflow_version={self.workflow_version_id}, channel={self.channel}, created_at={self.created_at}, updated_at={self.updated_at})"

class SubmissionModel(Base):
    __tablename__ = "submissions"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    workflow_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_versions.id"), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    subscriber_id_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    submitted_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        Index(
            "idx_submissions_org_flow",
            "organization_id",
            "workflow_version_id",
            "submitted_at",
        ),
    )
    
    def __repr__(self):
        return f"SubmissionModel(id={self.id}, workflow_id={self.workflow_id}, data={self.data}, created_at={self.created_at}, updated_at={self.updated_at})"