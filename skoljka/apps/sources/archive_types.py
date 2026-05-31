from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, TypedDict

from skoljka.apps.accounts.models import User

SCHEMA = "skoljka.archive.v1"
SummaryAction = Literal["create", "update", "skip", "overwrite", "delete", "keep"]
Action = SummaryAction | Literal["conflict"]
ProblemPolicy = Literal["overwrite", "skip"] | None
ConflictPolicy = Literal["overwrite", "skip"] | None
MissingAttachmentPolicy = Literal["delete", "keep"] | None
CountBucket = dict[str, int]


class ImportSummary(TypedDict):
    create: CountBucket
    update: CountBucket
    skip: CountBucket
    overwrite: CountBucket
    delete: CountBucket
    keep: CountBucket
    conflicts: int
    unaddressed_conflicts: int
    errors: int


@dataclass
class ExportOptions:
    source_slugs: list[str]
    output: str
    include_children: bool = True
    include_documents: bool = True
    include_attachments: bool = True
    public_only: bool = False


@dataclass
class ImportOptions:
    owner: User
    do_it: bool = False
    existing_problems: ProblemPolicy = None
    document_conflicts: ConflictPolicy = None
    attachment_conflicts: ConflictPolicy = None
    missing_attachments: MissingAttachmentPolicy = None
    create_missing_tags: bool = True
    update_existing_tags: bool = False
    ignore_missing_tags: bool = False
    force_public: bool | None = None


@dataclass
class PlannedChange:
    object_type: str
    identity: dict[str, Any]
    action: Action
    reason: str = ""
    available_actions: list[str] = field(default_factory=list)
    selected_action: SummaryAction | None = None
    existing: dict[str, Any] | None = None
    incoming: dict[str, Any] | None = None

    def unresolved(self) -> bool:
        return self.action == "conflict" and self.selected_action is None


@dataclass
class ImportPlan:
    schema: str
    mode: str
    policies: dict[str, Any]
    changes: list[PlannedChange] = field(default_factory=list)
    errors: list[PlannedChange] = field(default_factory=list)

    @property
    def conflicts(self) -> list[PlannedChange]:
        return [c for c in self.changes if c.action == "conflict"]

    @property
    def unaddressed_conflicts(self) -> int:
        return sum(1 for c in self.conflicts if c.selected_action is None)

    @property
    def can_apply(self) -> bool:
        return not self.errors and self.unaddressed_conflicts == 0

    def summary(self) -> ImportSummary:
        buckets: dict[SummaryAction, CountBucket] = {
            "create": {},
            "update": {},
            "skip": {},
            "overwrite": {},
            "delete": {},
            "keep": {},
        }
        for change in self.changes:
            bucket = change.selected_action or change.action
            if bucket == "conflict":
                continue
            counts = buckets[bucket]
            counts[change.object_type] = counts.get(change.object_type, 0) + 1
        return {
            "create": buckets["create"],
            "update": buckets["update"],
            "skip": buckets["skip"],
            "overwrite": buckets["overwrite"],
            "delete": buckets["delete"],
            "keep": buckets["keep"],
            "conflicts": len(self.conflicts),
            "unaddressed_conflicts": self.unaddressed_conflicts,
            "errors": len(self.errors),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "mode": self.mode,
            "can_apply": self.can_apply,
            "policies": self.policies,
            "summary": self.summary(),
            "changes": [asdict(c) for c in self.changes],
            "conflicts": [asdict(c) for c in self.conflicts],
            "errors": [asdict(e) for e in self.errors],
        }
