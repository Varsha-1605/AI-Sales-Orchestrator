"""Checks that run on every customer message before it reaches the agents."""

import re
import unicodedata
from typing import Callable, List, Tuple

from loguru import logger

from ai_workflow.settings import settings

# Each check takes the message and returns (blocked, reason).
InputCheck = Callable[[str], Tuple[bool, str]]

INJECTION_PATTERNS = [
    (
        "tries to override earlier instructions",
        r"\b(ignore|disregard|forget|override)\b.{0,30}\b(previous|prior|above|earlier|all|your)\b.{0,20}\b(instructions?|rules|prompts?|guidelines)\b",
    ),
    (
        "tries to override earlier instructions",
        r"\b(do not|don't|stop|never)\b.{0,10}\bfollow(ing)?\b.{0,25}\b(instructions?|rules|guidelines)\b",
    ),
    (
        "tries to override earlier instructions",
        r"\b(new|updated|real)\s+(instructions?|rules)\s*:",
    ),
    (
        "tries to override earlier instructions (Hinglish)",
        r"\b(pichle|purane|sabhi|saare)\b.{0,25}\b(instructions?|nirdesh|niyam|rules)\b",
    ),
    (
        "tries to change the assistant's role",
        r"\b(you are now|from now on you|from this point on you|pretend (to be|you are)|act as (if you|an? (unrestricted|different))|developer mode|jailbreak)",
    ),
    (
        "asks for the system prompt",
        r"\b(show|reveal|print|repeat|tell me|display|leak|output)\b.{0,30}\b(system prompt|your (instructions|prompt|rules)|initial prompt|hidden (rules|instructions|prompt))\b",
    ),
    (
        "asks for the system prompt",
        r"\b(repeat|print|output)\b.{0,20}\b(everything|the text)\b.{0,15}\b(above|before this)\b",
    ),
    (
        "tries to override a tool or price",
        r"\b((set|change|make|override)\b.{0,20}\bprice\b.{0,20}\b(to|as)\b|apply\b.{0,10}100\s*%\s*discount|skip\b.{0,15}\b(payment|approval)|bypass\b.{0,15}\b(payment|approval)|mark\b.{0,20}\bas paid)",
    ),
    (
        "contains hidden instruction markers",
        r"(<\|im_start\|>|<\|system\|>|\[/?INST\]|<system>|###\s*(system|instruction)|begin system prompt)",
    ),
]
COMPILED_PATTERNS = [(reason, re.compile(pattern, re.IGNORECASE)) for reason, pattern in INJECTION_PATTERNS]

HIDDEN_CHARACTERS = re.compile("[​-‏‪-‮⁠﻿]")


def normalize(message: str) -> str:
    """Undo tricks that hide text from the patterns: look-alike letters, invisible characters, odd spacing."""
    message = unicodedata.normalize("NFKC", message)
    message = HIDDEN_CHARACTERS.sub("", message)
    return re.sub(r"\s+", " ", message)


def check_prompt_injection(message: str) -> Tuple[bool, str]:
    message = normalize(message)
    for reason, pattern in COMPILED_PATTERNS:
        if pattern.search(message):
            return True, reason
    return False, ""


INPUT_CHECKS: List[InputCheck] = [check_prompt_injection]


def run_input_checks(message: str) -> Tuple[bool, str]:
    """Run every check. Returns (blocked, reason) for the first one that blocks."""
    if not settings.GUARDRAILS_ENABLED:
        return False, ""
    for check in INPUT_CHECKS:
        blocked, reason = check(message)
        if blocked:
            logger.warning("Message blocked: {}", reason)
            return True, reason
    return False, ""
