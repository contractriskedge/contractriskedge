"""ContractRiskEdge Python SDK.

Official Python client for the ContractRiskEdge API.

Usage:
    from contractai import Client

    client = Client(api_key="your-api-key")
    contracts = client.contracts.list()
    risks = client.risks.list(contract_id="...")
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx


@dataclass
class ClientConfig:
    """SDK client configuration."""

    api_key: str = ""
    base_url: str = "https://api.contractriskedge.com/api/v1"
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0


class APIError(Exception):
    """Raised when the API returns an error."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"API {status_code}: {message}")


class _ResourceBase:
    """Base class for API resource wrappers."""

    def __init__(self, client: "Client", path: str) -> None:
        self._client = client
        self._path = path

    def _url(self, *parts: str) -> str:
        return urljoin(
            self._client._config.base_url + "/",
            "/".join([self._path] + list(parts)),
        )

    def _request(
        self, method: str, url: str, **kwargs: Any
    ) -> Any:
        return self._client._request(method, url, **kwargs)


class ContractsResource(_ResourceBase):
    """Contract-related API methods."""

    def __init__(self, client: "Client") -> None:
        super().__init__(client, "contracts")

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List all contracts.

        Args:
            page: Page number.
            page_size: Items per page.
            status: Optional status filter.

        Returns:
            Dict with contracts list and pagination.
        """
        params = {"page": page, "page_size": page_size}
        if status:
            params["status"] = status
        return self._request("GET", self._url(), params=params)

    def get(self, contract_id: str) -> Dict[str, Any]:
        """Get a single contract by ID.

        Args:
            contract_id: The contract identifier.

        Returns:
            Contract data.
        """
        return self._request("GET", self._url(contract_id))

    def delete(self, contract_id: str) -> Dict[str, Any]:
        """Delete a contract.

        Args:
            contract_id: The contract identifier.

        Returns:
            Deletion confirmation.
        """
        return self._request("DELETE", self._url(contract_id))


class RisksResource(_ResourceBase):
    """Risk-related API methods."""

    def __init__(self, client: "Client") -> None:
        super().__init__(client, "risks")

    def list(
        self,
        contract_id: Optional[str] = None,
        category: Optional[str] = None,
        min_severity: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """List risk flags.

        Args:
            contract_id: Optional contract filter.
            category: Optional risk category filter.
            min_severity: Minimum severity filter.
            page: Page number.
            page_size: Items per page.

        Returns:
            Dict with risks list.
        """
        params = {"page": page, "page_size": page_size}
        if contract_id:
            params["contract_id"] = contract_id
        if category:
            params["category"] = category
        if min_severity:
            params["min_severity"] = min_severity
        return self._request("GET", self._url(), params=params)


class RedlinesResource(_ResourceBase):
    """Redline-related API methods."""

    def __init__(self, client: "Client") -> None:
        super().__init__(client, "redlines")

    def suggest(
        self,
        contract_id: str,
        clause_type: str,
        original_clause_text: str,
        party_role: str = "buyer",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate a redline suggestion.

        Args:
            contract_id: Contract identifier.
            clause_type: Type of clause.
            original_clause_text: The original clause text.
            party_role: Your role (buyer/seller).
            **kwargs: Additional parameters.

        Returns:
            Redline suggestion response.
        """
        payload = {
            "contract_id": contract_id,
            "clause_type": clause_type,
            "original_clause_text": original_clause_text,
            "party_role": party_role,
            **kwargs,
        }
        return self._request("POST", self._url("suggest"), json=payload)

    def accept(self, suggestion_id: str, comment: str = "") -> Dict[str, Any]:
        """Accept a redline suggestion.

        Args:
            suggestion_id: The suggestion to accept.
            comment: Optional comment.

        Returns:
            Updated suggestion status.
        """
        return self._request(
            "POST", self._url("suggest", suggestion_id, "accept"),
            json={"comment": comment},
        )

    def reject(self, suggestion_id: str, comment: str = "") -> Dict[str, Any]:
        """Reject a redline suggestion.

        Args:
            suggestion_id: The suggestion to reject.
            comment: Optional rejection reason.

        Returns:
            Updated suggestion status.
        """
        return self._request(
            "POST", self._url("suggest", suggestion_id, "reject"),
            json={"comment": comment},
        )


class BenchmarksResource(_ResourceBase):
    """Benchmark-related API methods."""

    def __init__(self, client: "Client") -> None:
        super().__init__(client, "benchmarks")

    def score(
        self,
        clause_text: str,
        clause_type: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Score a clause against market benchmarks.

        Args:
            clause_text: The clause text to score.
            clause_type: The type of clause.
            **kwargs: Optional segmentation params.

        Returns:
            Benchmark score with percentile.
        """
        params = {
            "clause_text": clause_text,
            "clause_type": clause_type,
            **kwargs,
        }
        return self._request("GET", self._url("score"), params=params)


class Client:
    """ContractRiskEdge API client.

    Usage:
        client = Client(api_key="sk-...")
        contracts = client.contracts.list()
        risks = client.risks.list(contract_id="...")
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.contractriskedge.com/api/v1",
        timeout: float = 30.0,
    ) -> None:
        """Initialize the API client.

        Args:
            api_key: API key for authentication.
            base_url: API base URL.
            timeout: Request timeout in seconds.
        """
        self._config = ClientConfig(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )
        self._http = httpx.Client(timeout=timeout)

        # Resource wrappers
        self.contracts = ContractsResource(self)
        self.risks = RisksResource(self)
        self.redlines = RedlinesResource(self)
        self.benchmarks = BenchmarksResource(self)

    def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> Any:
        """Make an HTTP request with retry logic.

        Args:
            method: HTTP method.
            url: Request URL.
            **kwargs: Additional request params.

        Returns:
            Response JSON.

        Raises:
            APIError: On API error response.
        """
        headers = kwargs.pop("headers", {})
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        last_error: Optional[Exception] = None

        for attempt in range(self._config.max_retries):
            try:
                response = self._http.request(
                    method, url, headers=headers, **kwargs
                )

                if response.status_code == 429:
                    retry_after = int(
                        response.headers.get("Retry-After", "1")
                    )
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as exc:
                last_error = APIError(
                    exc.response.status_code,
                    exc.response.text[:500],
                )
                if exc.response.status_code in (400, 401, 403, 404, 422):
                    raise last_error
                time.sleep(self._config.retry_delay * (2 ** attempt))

            except httpx.RequestError as exc:
                last_error = APIError(0, str(exc))
                time.sleep(self._config.retry_delay * (2 ** attempt))

        raise last_error or APIError(0, "Request failed")

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()
