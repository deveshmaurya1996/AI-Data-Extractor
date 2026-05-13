from ai.classifier import IntentClassifier


def test_classifier_orders_with_customer_uses_all_orders_template():
    classifier = IntentClassifier()
    result = classifier.classify("show me orders", has_customer=True, has_time_period=False)
    assert result.use_template is True
    assert result.template_key == "customer_orders_all"


def test_classifier_orders_without_customer_falls_back_to_ai():
    classifier = IntentClassifier()
    result = classifier.classify("show me orders", has_customer=False, has_time_period=False)
    assert result.use_template is False
    assert result.use_ai is True
