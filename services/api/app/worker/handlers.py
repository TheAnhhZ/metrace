# SPDX-FileCopyrightText: The metrace Authors
# SPDX-License-Identifier: Apache-2.0
"""Import point for every module that registers outbox handlers or reconcilers.

Domain phases add their modules here (incident recall, cold-chain alerts).
"""

from app.worker import incident_handlers  # noqa: F401
