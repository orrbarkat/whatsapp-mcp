-- Create devices table
CREATE TABLE devices (
    jid TEXT PRIMARY KEY,
    registration_id INTEGER,
    identity_public_key BYTEA,
    private_key BYTEA,
    adv_secret_key BYTEA,
    next_pre_key_id INTEGER,
    next_signed_pre_key_id INTEGER,
    last_pre_key_id_sent_to_server INTEGER,
    server_has_pre_keys_for_our_jid BOOLEAN,
    adv_data_timestamp_secs BIGINT,
    adv_key_index INTEGER,
    adv_data BYTEA,
    push_name TEXT,
    platform TEXT,
    business_name TEXT,
    fb_cat TEXT,
    fb_sub_cat TEXT,
    profile_pic_id TEXT,
    profile_pic_ts BIGINT,
    verification_level INTEGER,
    verification_details BYTEA,
    business_verified_name_ts BIGINT,
    business_verified_name_details BYTEA,
    business_is_api_initiated BOOLEAN,
    business_is_smb BOOLEAN,
    business_is_verified BOOLEAN,
    business_is_official BOOLEAN,
    business_is_eligible_for_name_verification BOOLEAN,
    business_is_eligible_for_official_app BOOLEAN,
    business_is_eligible_for_smb_official_app BOOLEAN,
    business_is_searchable BOOLEAN,
    business_is_one_time_password_enabled BOOLEAN,
    business_is_call_to_action_enabled BOOLEAN,
    business_is_consumer_messaging_enabled BOOLEAN,
    business_is_conversational_automation_enabled BOOLEAN,
    business_is_official_business_account_enabled BOOLEAN,
    business_is_payment_enabled BOOLEAN,
    business_is_catalog_enabled BOOLEAN,
    business_is_commerce_enabled BOOLEAN,
    business_is_small_business_enabled BOOLEAN,
    business_is_large_business_enabled BOOLEAN,
    business_is_enterprise_business_enabled BOOLEAN,
    business_is_customer_support_enabled BOOLEAN,
    business_is_marketing_enabled BOOLEAN,
    business_is_sales_enabled BOOLEAN,
    business_is_engagement_enabled BOOLEAN,
    business_is_lead_generation_enabled BOOLEAN,
    business_is_appointment_booking_enabled BOOLEAN,
    business_is_online_ordering_enabled BOOLEAN,
    business_is_delivery_enabled BOOLEAN,
    business_is_pickup_enabled BOOLEAN,
    business_is_reservations_enabled BOOLEAN,
    business_is_ticketing_enabled BOOLEAN,
    business_is_events_enabled BOOLEAN,
    business_is_donations_enabled BOOLEAN,
    business_is_fundraising_enabled BOOLEAN,
    business_is_volunteering_enabled BOOLEAN,
    business_is_community_enabled BOOLEAN,
    business_is_education_enabled BOOLEAN,
    business_is_government_enabled BOOLEAN,
    business_is_health_enabled BOOLEAN,
    business_is_non_profit_enabled BOOLEAN,
    business_is_religious_enabled BOOLEAN,
    business_is_political_enabled BOOLEAN,
    business_is_social_enabled BOOLEAN,
    business_is_other_enabled BOOLEAN
);

-- Create identities table
CREATE TABLE identities (
    recipient_id INTEGER NOT NULL,
    device_id INTEGER NOT NULL,
    identity_key BYTEA,
    PRIMARY KEY (recipient_id, device_id)
);

-- Create pre_keys table
CREATE TABLE pre_keys (
    pre_key_id INTEGER PRIMARY KEY,
    public_key BYTEA,
    private_key BYTEA,
    uploaded BOOLEAN
);

-- Create sessions table
CREATE TABLE sessions (
    recipient_id INTEGER NOT NULL,
    device_id INTEGER NOT NULL,
    session_data BYTEA,
    PRIMARY KEY (recipient_id, device_id)
);

-- Create signed_pre_keys table
CREATE TABLE signed_pre_keys (
    signed_pre_key_id INTEGER PRIMARY KEY,
    public_key BYTEA,
    private_key BYTEA,
    signature BYTEA,
    timestamp BIGINT
);

-- Create sender_keys table
CREATE TABLE sender_keys (
    group_id TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    sender_key_data BYTEA,
    PRIMARY KEY (group_id, sender_id)
);
