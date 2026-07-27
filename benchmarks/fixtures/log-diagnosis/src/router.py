def sms_destination(config: dict) -> str:
    service = config.get("messagingService")
    if service and not service.get("useInboundWebhookOnNumber", False):
        return service["inboundRequestUrl"]
    return config["smsWebhook"]
