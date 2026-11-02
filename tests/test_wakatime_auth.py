import unittest
from unittest.mock import patch

from kit import wakatime


class WakaTimeAuthTests(unittest.TestCase):
    def test_key_is_base64_encoded_in_authorization_header(self):
        with patch.object(wakatime, "default_client") as client:
            client.return_value.get_json.return_value = {"data": {}}
            wakatime.fetch_stats(api_key="example-key", api_domain="https://example.test")
        kwargs = client.return_value.get_json.call_args.kwargs
        self.assertEqual(kwargs["headers"]["Authorization"], "Basic ZXhhbXBsZS1rZXk=")
        self.assertIs(kwargs["cache"], False)

    def test_http_endpoint_is_rejected_before_sending_credentials(self):
        with patch.object(wakatime, "default_client") as client:
            self.assertIsNone(wakatime.fetch_stats(api_key="example-key", api_domain="http://example.test"))
        client.assert_not_called()
