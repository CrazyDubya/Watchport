from __future__ import annotations

from base64 import urlsafe_b64decode

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)


def b64url_decode(value: str) -> bytes:
    return urlsafe_b64decode(value + "=" * (-len(value) % 4))


class WebAuthnService:
    def __init__(self, rp_id: str, origin: str, store):
        self.rp_id = rp_id
        self.origin = origin
        self.store = store

    def registration_options(self, challenge: bytes) -> str:
        options = generate_registration_options(
            rp_id=self.rp_id,
            rp_name="Watchport",
            user_id=b"watchport-owner",
            user_name="owner",
            user_display_name="Watchport owner",
            challenge=challenge,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
        )
        return options_to_json(options)

    def verify_registration(self, response: dict, challenge: bytes) -> None:
        result = verify_registration_response(
            credential=response,
            expected_challenge=challenge,
            expected_rp_id=self.rp_id,
            expected_origin=self.origin,
            require_user_verification=True,
        )
        self.store.put(result.credential_id, result.credential_public_key, result.sign_count)

    def authentication_options(self, challenge: bytes) -> str:
        options = generate_authentication_options(
            rp_id=self.rp_id,
            challenge=challenge,
            allow_credentials=[
                PublicKeyCredentialDescriptor(id=c["credential_id"]) for c in self.store.all()
            ],
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        return options_to_json(options)

    def verify_authentication(self, response: dict, challenge: bytes) -> None:
        credential_id = b64url_decode(response["id"])
        stored = self.store.get(credential_id)
        if not stored:
            raise ValueError("unknown credential")
        result = verify_authentication_response(
            credential=response,
            expected_challenge=challenge,
            expected_rp_id=self.rp_id,
            expected_origin=self.origin,
            credential_public_key=stored["public_key"],
            credential_current_sign_count=stored["sign_count"],
            require_user_verification=True,
        )
        self.store.update_sign_count(credential_id, result.new_sign_count)
