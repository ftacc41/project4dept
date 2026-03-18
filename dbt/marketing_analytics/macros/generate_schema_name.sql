-- Override dbt's default schema naming to use the custom schema name directly
-- without prepending the target dataset. This ensures staging models go to
-- the `staging` dataset and mart models go to the `marts` dataset as intended.
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.dataset }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
