from crypto_mas.services.feature_pipeline.schemas import FeatureSetSchema

def test_feature_set_schema_defaults():
    data = {"close": 50000.0, "rsi_14": 55.4}
    schema = FeatureSetSchema.model_validate(data)
    assert schema.close == 50000.0
    assert schema.rsi_14 == 55.4
    assert schema.atr_14 is None
    assert schema.sma_20 is None

def test_feature_set_schema_extra_fields():
    data = {
        "close": 100.0,
        "custom_indicator": 123.45
    }
    schema = FeatureSetSchema.model_validate(data)
    assert schema.close == 100.0
    dumped = schema.to_dict()
    assert dumped["custom_indicator"] == 123.45
