# Stream adapter completion contract

The next implementation slice must replace the static `WATCHPORT_VIEWER_URL` handoff with a real adapter that owns the lifecycle of a backend-enforced Moonlight-Web Viewer capability.

Required interface:

```python
class StreamAdapter:
    def create_viewer(self, session_id: str) -> ViewerCapability: ...
    def revoke_viewer(self, session_id: str) -> None: ...
    def is_active(self, session_id: str) -> bool: ...
```

`ViewerCapability` must be view-only below the browser UI layer and must contain only the minimum material required by the browser to connect.

Required behavior:

- create only Viewer permissions; never Gamer or Full Control;
- no clipboard/input/file/shell authority;
- revoke when Watchport session expires;
- revoke when the user closes the view;
- revoke when indicator heartbeat becomes unhealthy beyond the grace period;
- revoke stale capabilities on gateway startup where possible;
- never enable Moonlight-Web Internet Access/UPnP/public ingress;
- keep Moonlight-Web/Sunshine as separately installed GPL dependencies.

Acceptance test: kill the indicator process while a real remote browser is viewing. The video must stop without requiring action in the browser and without leaving a reusable Viewer capability behind.
