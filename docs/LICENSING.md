# Licensing Notes

This document is an engineering guide, not legal advice.

## Watchport original code

New original code written specifically for Watchport is intended to be licensed under the **MIT License** unless a file or component explicitly states otherwise.

## External components

### Tailscale

Tailscale is an external networking dependency/service. Watchport should integrate with an installed Tailscale client and tailnet policy rather than embedding Tailscale source code.

The Tailscale client source includes open-source components under its published licensing terms, while the broader Tailscale service/product has its own terms. Treat Tailscale as an external prerequisite unless a future design intentionally links or vendors source.

### Sunshine

Sunshine is distributed under **GPL-3.0** terms.

Preferred Watchport integration model:

- Sunshine installed separately
- Watchport communicates/configures through documented runtime interfaces
- do not copy Sunshine source into MIT-licensed Watchport components
- do not statically combine Sunshine GPL code with Watchport code without first reviewing the resulting licensing obligations

### Moonlight / browser streaming bridges

Moonlight-derived or Moonlight-compatible projects have their own licenses. The browser candidate investigated for the initial architecture may be GPL-licensed.

Before selecting or importing any browser bridge:

1. record exact upstream repository and version/commit
2. verify its current LICENSE file
3. decide whether Watchport will invoke it as a separate process/service, distribute it alongside Watchport, fork it, or incorporate source
4. preserve notices/source-offer obligations as required by its license

Do not assume that because a project is publicly available on GitHub its code can be copied into an MIT repository without conditions.

## Dependency rule for agents

Before introducing a new runtime or source dependency, add an entry here containing:

- project
- upstream URL
- exact license
- integration form (external process, network service, dynamically linked library, copied source, etc.)
- redistribution implications

## Architectural licensing preference

Watchport should prefer clean runtime boundaries around strong copyleft components when that boundary also makes architectural sense.

This is not an attempt to evade license obligations. It is meant to keep ownership and obligations of independently distributed components clear and to avoid accidentally relicensing original Watchport code through unnecessary source incorporation.

If Watchport eventually forks a GPL component or creates a derivative work, that component should be distributed under the required GPL-compatible terms with source and notices provided accordingly.
