select
  usage.usage_metadata.endpoint_id,
  usage.usage_metadata.endpoint_name,
  usage.usage_metadata.app_id,
  usage.usage_metadata.app_name,
  usage.sku_name,
  usage.usage_date,
  usage.product_features.serving_type,
  usage_type,
  billing_origin_product,
  usage_quantity,
  usage.identity_metadata.run_as,
  usage.usage_quantity * list_prices.pricing.effective_list.default as cost
from
  system.billing.usage
  left JOIN system.billing.list_prices ON list_prices.sku_name = usage.sku_name
WHERE
  usage.usage_end_time >= list_prices.price_start_time
  AND (
    list_prices.price_end_time IS NULL
    OR usage.usage_end_time < list_prices.price_end_time
  )
  AND usage.workspace_id = ....
  AND usage.usage_date >= CURRENT_DATE() - INTERVAL 30 DAY