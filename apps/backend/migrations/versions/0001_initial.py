"""Frozen initial 33-table MySQL schema. Do not import live ORM models here."""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE TABLE users (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\temail_lookup_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin, \n\temail_ciphertext TEXT, \n\temail_verified_at DATETIME(6), \n\tdisplay_name VARCHAR(40) NOT NULL, \n\tbio VARCHAR(300) NOT NULL, \n\tavatar_asset_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tcity_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tstatus VARCHAR(20) NOT NULL, \n\tterms_version VARCHAR(40) NOT NULL, \n\tterms_accepted_at DATETIME(6) NOT NULL, \n\tdeleted_at DATETIME(6), \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_users PRIMARY KEY (id), \n\tCONSTRAINT uq_users_email_lookup_hash UNIQUE (email_lookup_hash), \n\tCONSTRAINT ck_users_email CHECK ((status='deleted' AND email_lookup_hash IS NULL AND email_ciphertext IS NULL AND email_verified_at IS NULL) OR (status IN ('active','suspended') AND email_lookup_hash IS NOT NULL AND email_ciphertext IS NOT NULL AND email_verified_at IS NOT NULL))\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE user_roles (\n\tuser_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\t`role` VARCHAR(20) NOT NULL, \n\tgranted_by CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_user_roles PRIMARY KEY (user_id, `role`), \n\tCONSTRAINT ck_user_roles_role CHECK (role IN ('editor','moderator','admin'))\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE auth_send_limits (\n\temail_lookup_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tpurpose VARCHAR(30) NOT NULL, \n\tnext_allowed_at DATETIME(6) NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_auth_send_limits PRIMARY KEY (email_lookup_hash, purpose)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE auth_challenges (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\temail_lookup_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\temail_ciphertext TEXT NOT NULL, \n\tpurpose VARCHAR(30) NOT NULL, \n\tcode_hmac CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tdelivery_code_ciphertext TEXT, \n\texpires_at DATETIME(6) NOT NULL, \n\tattempts SMALLINT UNSIGNED NOT NULL, \n\tmax_attempts SMALLINT UNSIGNED NOT NULL, \n\tconsumed_at DATETIME(6), \n\tdelivery_status VARCHAR(20) NOT NULL, \n\tterms_version VARCHAR(40), \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_auth_challenges PRIMARY KEY (id), \n\tCONSTRAINT ck_auth_challenges_purpose CHECK (purpose IN ('login','delete_account'))\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE INDEX ix_auth_challenges_email_lookup_hash_purpose_cre_e9e92fe9 ON auth_challenges (email_lookup_hash, purpose, created_at)"
    )
    op.execute(
        "CREATE TABLE auth_sessions (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tuser_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tclient_type VARCHAR(20) NOT NULL, \n\tdevice_label VARCHAR(100) NOT NULL, \n\tlast_seen_at DATETIME(6) NOT NULL, \n\tabsolute_expires_at DATETIME(6) NOT NULL, \n\trevoked_at DATETIME(6), \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_auth_sessions PRIMARY KEY (id), \n\tCONSTRAINT ck_auth_sessions_client_type CHECK (client_type IN ('mobile','editor_web'))\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE INDEX ix_auth_sessions_user_id_revoked_at_5aa97930 ON auth_sessions (user_id, revoked_at)"
    )
    op.execute(
        "CREATE TABLE refresh_tokens (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tsession_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\ttoken_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tparent_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\texpires_at DATETIME(6) NOT NULL, \n\tused_at DATETIME(6), \n\trevoked_at DATETIME(6), \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_refresh_tokens PRIMARY KEY (id), \n\tCONSTRAINT uq_refresh_tokens_token_hash UNIQUE (token_hash), \n\tCONSTRAINT uq_refresh_tokens_parent_id UNIQUE (parent_id)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE cities (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tcode VARCHAR(32) NOT NULL, \n\tname VARCHAR(80) NOT NULL, \n\tcountry_code CHAR(2) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\ttimezone VARCHAR(64) NOT NULL, \n\tenabled BOOL NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_cities PRIMARY KEY (id), \n\tCHECK (enabled IN (0, 1)), \n\tCONSTRAINT uq_cities_code UNIQUE (code)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE districts (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tcity_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tcode VARCHAR(32) NOT NULL, \n\tname VARCHAR(80) NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_districts PRIMARY KEY (id), \n\tCONSTRAINT uq_districts_city_id_code UNIQUE (city_id, code), \n\tCONSTRAINT uq_districts_id_city_id UNIQUE (id, city_id)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE places (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tcity_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tdistrict_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tname VARCHAR(200) NOT NULL, \n\taddress VARCHAR(500) NOT NULL, \n\tlatitude DECIMAL(9, 6), \n\tlongitude DECIMAL(9, 6), \n\tsummary VARCHAR(500) NOT NULL, \n\topening_hours_text VARCHAR(1000) NOT NULL, \n\ttransport_notes VARCHAR(1000) NOT NULL, \n\tcover_asset_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tsource_url VARCHAR(2048), \n\tverified_at DATETIME(6), \n\tstatus VARCHAR(20) NOT NULL, \n\tversion INTEGER UNSIGNED NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_places PRIMARY KEY (id), \n\tCONSTRAINT uq_places_id_city_id UNIQUE (id, city_id), \n\tCONSTRAINT ck_places_coords CHECK ((latitude IS NULL AND longitude IS NULL) OR (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180))\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE INDEX ix_places_city_id_district_id_status_ae834654 ON places (city_id, district_id, status)"
    )
    op.execute(
        "CREATE TABLE place_assets (\n\tplace_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tasset_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tposition INTEGER UNSIGNED NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_place_assets PRIMARY KEY (place_id, asset_id), \n\tCONSTRAINT uq_place_assets_place_id_position UNIQUE (place_id, position)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE events (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tcity_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tplace_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\ttitle VARCHAR(200) NOT NULL, \n\tdescription TEXT NOT NULL, \n\torganizer VARCHAR(200), \n\tbooking_url VARCHAR(2048), \n\tprice_status VARCHAR(20) NOT NULL, \n\tprice_min_fen INTEGER UNSIGNED, \n\tprice_max_fen INTEGER UNSIGNED, \n\tcurrency CHAR(3) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tsource_url VARCHAR(2048), \n\tverified_at DATETIME(6), \n\tstatus VARCHAR(20) NOT NULL, \n\tversion INTEGER UNSIGNED NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_events PRIMARY KEY (id), \n\tCONSTRAINT ck_events_price CHECK ((price_status='unknown' AND price_min_fen IS NULL AND price_max_fen IS NULL) OR (price_status='free' AND price_min_fen=0 AND price_max_fen=0) OR (price_status='known' AND price_min_fen IS NOT NULL AND price_max_fen IS NOT NULL AND price_min_fen<=price_max_fen))\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute("CREATE INDEX ix_events_city_id_status_e1172918 ON events (city_id, status)")
    op.execute(
        "CREATE TABLE event_sessions (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tevent_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tstarts_at DATETIME(6) NOT NULL, \n\tends_at DATETIME(6) NOT NULL, \n\tentry_note VARCHAR(500) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tversion INTEGER UNSIGNED NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_event_sessions PRIMARY KEY (id), \n\tCONSTRAINT uq_event_sessions_id_event_id UNIQUE (id, event_id), \n\tCONSTRAINT uq_event_sessions_event_id_starts_at_ends_at UNIQUE (event_id, starts_at, ends_at), \n\tCONSTRAINT ck_event_sessions_time CHECK (ends_at > starts_at)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE INDEX ix_event_sessions_event_id_status_starts_at_38c57e10 ON event_sessions (event_id, status, starts_at)"
    )
    op.execute(
        "CREATE TABLE tags (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tslug VARCHAR(64) NOT NULL, \n\tname VARCHAR(40) NOT NULL, \n\tcategory VARCHAR(30) NOT NULL, \n\tenabled BOOL NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_tags PRIMARY KEY (id), \n\tCHECK (enabled IN (0, 1)), \n\tCONSTRAINT uq_tags_slug UNIQUE (slug)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE media_assets (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\towner_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tkind VARCHAR(20) NOT NULL, \n\tpurpose VARCHAR(30) NOT NULL, \n\tstorage_key VARCHAR(255) NOT NULL, \n\tverified_mime VARCHAR(80), \n\tsize_bytes BIGINT UNSIGNED, \n\twidth INTEGER UNSIGNED, \n\theight INTEGER UNSIGNED, \n\tduration_ms BIGINT UNSIGNED, \n\tstatus VARCHAR(20) NOT NULL, \n\tvisibility VARCHAR(20) NOT NULL, \n\tvariants JSON NOT NULL, \n\trejection_code VARCHAR(80), \n\tupload_expires_at DATETIME(6) NOT NULL, \n\tdeleted_at DATETIME(6), \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_media_assets PRIMARY KEY (id), \n\tCONSTRAINT uq_media_assets_storage_key UNIQUE (storage_key), \n\tCONSTRAINT ck_media_assets_kind CHECK (kind IN ('image','video') AND (kind <> 'video' OR purpose='editorial_media')), \n\tCONSTRAINT ck_media_assets_purpose CHECK (purpose IN ('note_image','editorial_media','place_image','avatar'))\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute("CREATE INDEX ix_media_assets_owner_id_status_887219ee ON media_assets (owner_id, status)")
    op.execute(
        "CREATE TABLE editor_articles (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tauthor_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tcity_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tdistrict_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tstatus VARCHAR(20) NOT NULL, \n\tpublished_revision_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tfirst_published_at DATETIME(6), \n\tpublished_at DATETIME(6), \n\teditorial_rank INTEGER NOT NULL, \n\tversion INTEGER UNSIGNED NOT NULL, \n\tdeleted_at DATETIME(6), \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_editor_articles PRIMARY KEY (id), \n\tCONSTRAINT ck_editor_articles_published CHECK (status <> 'published' OR (published_revision_id IS NOT NULL AND first_published_at IS NOT NULL AND published_at IS NOT NULL))\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE INDEX ix_editor_articles_city_id_district_id_status_ed_8a991e62 ON editor_articles (city_id, district_id, status, editorial_rank, first_published_at, id)"
    )
    op.execute(
        "CREATE TABLE editor_drafts (\n\tarticle_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\ttitle VARCHAR(150) NOT NULL, \n\tsubtitle VARCHAR(200) NOT NULL, \n\tsummary VARCHAR(500) NOT NULL, \n\tfocus_type VARCHAR(20), \n\tprimary_place_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tprimary_event_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tdocument JSON NOT NULL, \n\tdocument_schema_version SMALLINT UNSIGNED NOT NULL, \n\tcover_asset_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\ttag_ids JSON NOT NULL, \n\tedit_version INTEGER UNSIGNED NOT NULL, \n\tlast_edited_by CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_editor_drafts PRIMARY KEY (article_id), \n\tCONSTRAINT ck_editor_drafts_focus CHECK ((focus_type IS NULL AND primary_place_id IS NULL AND primary_event_id IS NULL) OR (focus_type='place' AND primary_event_id IS NULL) OR (focus_type='event' AND primary_place_id IS NULL))\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE editor_revisions (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tarticle_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\trevision_no INTEGER UNSIGNED NOT NULL, \n\tbased_on_edit_version INTEGER UNSIGNED NOT NULL, \n\ttitle VARCHAR(150) NOT NULL, \n\tsubtitle VARCHAR(200) NOT NULL, \n\tsummary VARCHAR(500) NOT NULL, \n\tfocus_type VARCHAR(20) NOT NULL, \n\tprimary_place_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tprimary_event_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tdocument JSON NOT NULL, \n\tdocument_schema_version SMALLINT UNSIGNED NOT NULL, \n\tplain_text MEDIUMTEXT NOT NULL, \n\tcover_asset_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tsubmitted_by CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_editor_revisions PRIMARY KEY (id), \n\tCONSTRAINT uq_editor_revisions_article_id_revision_no UNIQUE (article_id, revision_no), \n\tCONSTRAINT uq_editor_revisions_article_id_based_on_edit_version UNIQUE (article_id, based_on_edit_version), \n\tCONSTRAINT uq_editor_revisions_id_article_id UNIQUE (id, article_id), \n\tCONSTRAINT ck_editor_revisions_focus CHECK ((focus_type='place' AND primary_place_id IS NOT NULL AND primary_event_id IS NULL) OR (focus_type='event' AND primary_event_id IS NOT NULL AND primary_place_id IS NULL))\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE editor_revision_tags (\n\trevision_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\ttag_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_editor_revision_tags PRIMARY KEY (revision_id, tag_id)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE editor_revision_assets (\n\trevision_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tasset_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\t`role` VARCHAR(20) NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_editor_revision_assets PRIMARY KEY (revision_id, asset_id, `role`)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE editor_reviews (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\trevision_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\treviewer_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\treason_code VARCHAR(80), \n\treviewer_note TEXT, \n\tautomated_findings JSON NOT NULL, \n\treviewed_at DATETIME(6), \n\tversion INTEGER UNSIGNED NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_editor_reviews PRIMARY KEY (id), \n\tCONSTRAINT uq_editor_reviews_revision_id UNIQUE (revision_id), \n\tCONSTRAINT ck_editor_reviews_review CHECK ((status='pending' AND reviewed_at IS NULL) OR (status='approved' AND reviewed_at IS NOT NULL) OR (status='rejected' AND reviewed_at IS NOT NULL AND reason_code IS NOT NULL)), \n\tCONSTRAINT ck_editor_reviews_reviewer CHECK (status='pending' OR reviewer_id IS NOT NULL)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE INDEX ix_editor_reviews_status_created_at_2f833b99 ON editor_reviews (status, created_at)"
    )
    op.execute(
        "CREATE TABLE notes (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tauthor_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tcity_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\ttitle VARCHAR(100) NOT NULL, \n\tbody_text TEXT NOT NULL, \n\tplace_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tevent_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tstatus VARCHAR(20) NOT NULL, \n\tpublished_submission_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tfirst_published_at DATETIME(6), \n\tpublished_at DATETIME(6), \n\tversion INTEGER UNSIGNED NOT NULL, \n\tdeleted_at DATETIME(6), \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_notes PRIMARY KEY (id), \n\tCONSTRAINT ck_notes_published CHECK (status <> 'published' OR (published_submission_id IS NOT NULL AND first_published_at IS NOT NULL AND published_at IS NOT NULL))\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE INDEX ix_notes_city_id_status_first_published_at_id_e6c471df ON notes (city_id, status, first_published_at, id)"
    )
    op.execute("CREATE INDEX ix_notes_author_id_created_at_c7fb91b7 ON notes (author_id, created_at)")
    op.execute(
        "CREATE TABLE note_images (\n\tnote_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tasset_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tposition INTEGER UNSIGNED NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_note_images PRIMARY KEY (note_id, asset_id), \n\tCONSTRAINT uq_note_images_note_id_position UNIQUE (note_id, position), \n\tCONSTRAINT ck_note_images_position CHECK (position <= 8)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE note_drafts (\n\tnote_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\ttitle VARCHAR(100) NOT NULL, \n\tbody_text TEXT NOT NULL, \n\timage_ids JSON NOT NULL, \n\tplace_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tevent_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tedit_version INTEGER UNSIGNED NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_note_drafts PRIMARY KEY (note_id)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE note_submissions (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tnote_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tsubmission_no INTEGER UNSIGNED NOT NULL, \n\tbased_on_edit_version INTEGER UNSIGNED NOT NULL, \n\ttitle VARCHAR(100) NOT NULL, \n\tbody_text TEXT NOT NULL, \n\timage_ids JSON NOT NULL, \n\tplace_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tevent_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tstatus VARCHAR(20) NOT NULL, \n\treviewer_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\treason_code VARCHAR(80), \n\treviewer_note TEXT, \n\tautomated_findings JSON NOT NULL, \n\treviewed_at DATETIME(6), \n\treview_version INTEGER UNSIGNED NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_note_submissions PRIMARY KEY (id), \n\tCONSTRAINT uq_note_submissions_note_id_submission_no UNIQUE (note_id, submission_no), \n\tCONSTRAINT uq_note_submissions_note_id_based_on_edit_version UNIQUE (note_id, based_on_edit_version), \n\tCONSTRAINT uq_note_submissions_id_note_id UNIQUE (id, note_id), \n\tCONSTRAINT ck_note_submissions_review CHECK ((status='pending' AND reviewed_at IS NULL) OR (status='approved' AND reviewed_at IS NOT NULL) OR (status='rejected' AND reviewed_at IS NOT NULL AND reason_code IS NOT NULL))\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE INDEX ix_note_submissions_status_created_at_2f833b99 ON note_submissions (status, created_at)"
    )
    op.execute(
        "CREATE TABLE note_reactions (\n\tuser_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tnote_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tkind VARCHAR(20) NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_note_reactions PRIMARY KEY (user_id, note_id, kind), \n\tCONSTRAINT ck_note_reactions_kind CHECK (kind IN ('like','bookmark'))\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE editor_article_reactions (\n\tuser_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tarticle_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tkind VARCHAR(20) NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_editor_article_reactions PRIMARY KEY (user_id, article_id, kind), \n\tCONSTRAINT ck_editor_article_reactions_kind CHECK (kind IN ('like','bookmark'))\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE event_participations (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tuser_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tevent_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tsession_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tstate VARCHAR(20) NOT NULL, \n\tattended_at DATETIME(6), \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_event_participations PRIMARY KEY (id), \n\tCONSTRAINT uq_event_participations_user_id_event_id UNIQUE (user_id, event_id), \n\tCONSTRAINT ck_event_participations_state CHECK ((state='interested' AND attended_at IS NULL) OR (state='attended' AND attended_at IS NOT NULL))\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE user_blocks (\n\tuser_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tblocked_user_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_user_blocks PRIMARY KEY (user_id, blocked_user_id), \n\tCONSTRAINT ck_user_blocks_self CHECK (user_id <> blocked_user_id)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE note_reports (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\treporter_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tnote_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tsubmission_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\treason VARCHAR(30) NOT NULL, \n\tdescription VARCHAR(1000) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tresolved_by CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tresolution_note TEXT, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_note_reports PRIMARY KEY (id)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE editor_article_reports (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\treporter_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tarticle_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\trevision_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\treason VARCHAR(30) NOT NULL, \n\tdescription VARCHAR(1000) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tresolved_by CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\tresolution_note TEXT, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_editor_article_reports PRIMARY KEY (id)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE jobs (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tkind VARCHAR(30) NOT NULL, \n\ttarget_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tdedupe_key VARCHAR(191) NOT NULL, \n\tpayload JSON NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tattempts INTEGER UNSIGNED NOT NULL, \n\tmax_attempts INTEGER UNSIGNED NOT NULL, \n\tavailable_at DATETIME(6) NOT NULL, \n\tlease_owner VARCHAR(100), \n\tlease_until DATETIME(6), \n\tlast_error_code VARCHAR(80), \n\tfinished_at DATETIME(6), \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_jobs PRIMARY KEY (id), \n\tCONSTRAINT uq_jobs_dedupe_key UNIQUE (dedupe_key)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute("CREATE INDEX ix_jobs_status_available_at_id_47c97f82 ON jobs (status, available_at, id)")
    op.execute("CREATE INDEX ix_jobs_status_lease_until_d3ec8fd1 ON jobs (status, lease_until)")
    op.execute(
        "CREATE TABLE idempotency_records (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tuser_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\toperation VARCHAR(80) NOT NULL, \n\trequest_key VARCHAR(100) NOT NULL, \n\trequest_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tresource_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tresponse_status SMALLINT UNSIGNED NOT NULL, \n\texpires_at DATETIME(6) NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_idempotency_records PRIMARY KEY (id), \n\tCONSTRAINT uq_idempotency_records_user_id_operation_request_key UNIQUE (user_id, operation, request_key)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE TABLE audit_logs (\n\tid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tactor_type VARCHAR(20) NOT NULL, \n\tactor_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, \n\taction VARCHAR(80) NOT NULL, \n\ttarget_type VARCHAR(50) NOT NULL, \n\ttarget_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\tbefore_summary JSON, \n\tafter_summary JSON, \n\trequest_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, \n\treason TEXT, \n\tcreated_at DATETIME(6) NOT NULL, \n\tCONSTRAINT pk_audit_logs PRIMARY KEY (id)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    op.execute(
        "CREATE INDEX ix_audit_logs_target_type_target_id_created_at_180e659b ON audit_logs (target_type, target_id, created_at)"
    )
    op.execute(
        "ALTER TABLE editor_articles ADD CONSTRAINT fk_editor_articles_city_id_cities FOREIGN KEY(city_id) REFERENCES cities (id)"
    )
    op.execute(
        "ALTER TABLE districts ADD CONSTRAINT fk_districts_city_id_cities FOREIGN KEY(city_id) REFERENCES cities (id)"
    )
    op.execute(
        "ALTER TABLE refresh_tokens ADD CONSTRAINT fk_refresh_tokens_parent_id_refresh_tokens FOREIGN KEY(parent_id) REFERENCES refresh_tokens (id)"
    )
    op.execute(
        "ALTER TABLE places ADD CONSTRAINT fk_place_district_city FOREIGN KEY(district_id, city_id) REFERENCES districts (id, city_id)"
    )
    op.execute(
        "ALTER TABLE note_drafts ADD CONSTRAINT fk_note_drafts_event_id_events FOREIGN KEY(event_id) REFERENCES events (id)"
    )
    op.execute(
        "ALTER TABLE note_submissions ADD CONSTRAINT fk_note_submissions_event_id_events FOREIGN KEY(event_id) REFERENCES events (id)"
    )
    op.execute(
        "ALTER TABLE editor_article_reports ADD CONSTRAINT fk_report_article_revision FOREIGN KEY(revision_id, article_id) REFERENCES editor_revisions (id, article_id)"
    )
    op.execute(
        "ALTER TABLE editor_revisions ADD CONSTRAINT fk_editor_revisions_submitted_by_users FOREIGN KEY(submitted_by) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE place_assets ADD CONSTRAINT fk_place_assets_place_id_places FOREIGN KEY(place_id) REFERENCES places (id)"
    )
    op.execute(
        "ALTER TABLE editor_articles ADD CONSTRAINT fk_editor_articles_district_id_districts FOREIGN KEY(district_id) REFERENCES districts (id)"
    )
    op.execute(
        "ALTER TABLE editor_drafts ADD CONSTRAINT fk_editor_drafts_article_id_editor_articles FOREIGN KEY(article_id) REFERENCES editor_articles (id)"
    )
    op.execute(
        "ALTER TABLE user_roles ADD CONSTRAINT fk_user_roles_granted_by_users FOREIGN KEY(granted_by) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE note_submissions ADD CONSTRAINT fk_note_submissions_reviewer_id_users FOREIGN KEY(reviewer_id) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE places ADD CONSTRAINT fk_places_cover_asset_id_media_assets FOREIGN KEY(cover_asset_id) REFERENCES media_assets (id)"
    )
    op.execute(
        "ALTER TABLE place_assets ADD CONSTRAINT fk_place_assets_asset_id_media_assets FOREIGN KEY(asset_id) REFERENCES media_assets (id)"
    )
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT fk_users_city_id_cities FOREIGN KEY(city_id) REFERENCES cities (id)"
    )
    op.execute(
        "ALTER TABLE events ADD CONSTRAINT fk_event_place_city FOREIGN KEY(place_id, city_id) REFERENCES places (id, city_id)"
    )
    op.execute(
        "ALTER TABLE editor_drafts ADD CONSTRAINT fk_editor_drafts_primary_place_id_places FOREIGN KEY(primary_place_id) REFERENCES places (id)"
    )
    op.execute(
        "ALTER TABLE editor_revision_tags ADD CONSTRAINT fk_editor_revision_tags_revision_id_editor_revisions FOREIGN KEY(revision_id) REFERENCES editor_revisions (id)"
    )
    op.execute(
        "ALTER TABLE note_images ADD CONSTRAINT fk_note_images_note_id_notes FOREIGN KEY(note_id) REFERENCES notes (id)"
    )
    op.execute(
        "ALTER TABLE event_participations ADD CONSTRAINT fk_event_participations_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE notes ADD CONSTRAINT fk_note_own_submission FOREIGN KEY(published_submission_id, id) REFERENCES note_submissions (id, note_id)"
    )
    op.execute(
        "ALTER TABLE editor_drafts ADD CONSTRAINT fk_editor_drafts_primary_event_id_events FOREIGN KEY(primary_event_id) REFERENCES events (id)"
    )
    op.execute(
        "ALTER TABLE event_participations ADD CONSTRAINT fk_participation_session_event FOREIGN KEY(session_id, event_id) REFERENCES event_sessions (id, event_id)"
    )
    op.execute(
        "ALTER TABLE editor_revision_tags ADD CONSTRAINT fk_editor_revision_tags_tag_id_tags FOREIGN KEY(tag_id) REFERENCES tags (id)"
    )
    op.execute(
        "ALTER TABLE note_images ADD CONSTRAINT fk_note_images_asset_id_media_assets FOREIGN KEY(asset_id) REFERENCES media_assets (id)"
    )
    op.execute(
        "ALTER TABLE event_participations ADD CONSTRAINT fk_event_participations_event_id_events FOREIGN KEY(event_id) REFERENCES events (id)"
    )
    op.execute(
        "ALTER TABLE places ADD CONSTRAINT fk_places_city_id_cities FOREIGN KEY(city_id) REFERENCES cities (id)"
    )
    op.execute(
        "ALTER TABLE idempotency_records ADD CONSTRAINT fk_idempotency_records_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE note_reactions ADD CONSTRAINT fk_note_reactions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE note_reports ADD CONSTRAINT fk_note_reports_reporter_id_users FOREIGN KEY(reporter_id) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT fk_users_avatar_asset_id_media_assets FOREIGN KEY(avatar_asset_id) REFERENCES media_assets (id)"
    )
    op.execute(
        "ALTER TABLE editor_drafts ADD CONSTRAINT fk_editor_drafts_cover_asset_id_media_assets FOREIGN KEY(cover_asset_id) REFERENCES media_assets (id)"
    )
    op.execute(
        "ALTER TABLE media_assets ADD CONSTRAINT fk_media_assets_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE event_participations ADD CONSTRAINT fk_event_participations_session_id_event_sessions FOREIGN KEY(session_id) REFERENCES event_sessions (id)"
    )
    op.execute(
        "ALTER TABLE places ADD CONSTRAINT fk_places_district_id_districts FOREIGN KEY(district_id) REFERENCES districts (id)"
    )
    op.execute(
        "ALTER TABLE events ADD CONSTRAINT fk_events_city_id_cities FOREIGN KEY(city_id) REFERENCES cities (id)"
    )
    op.execute(
        "ALTER TABLE editor_revision_assets ADD CONSTRAINT fk_editor_revision_assets_revision_id_editor_revisions FOREIGN KEY(revision_id) REFERENCES editor_revisions (id)"
    )
    op.execute(
        "ALTER TABLE note_reactions ADD CONSTRAINT fk_note_reactions_note_id_notes FOREIGN KEY(note_id) REFERENCES notes (id)"
    )
    op.execute(
        "ALTER TABLE note_reports ADD CONSTRAINT fk_note_reports_note_id_notes FOREIGN KEY(note_id) REFERENCES notes (id)"
    )
    op.execute(
        "ALTER TABLE editor_article_reports ADD CONSTRAINT fk_editor_article_reports_reporter_id_users FOREIGN KEY(reporter_id) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE editor_drafts ADD CONSTRAINT fk_editor_drafts_last_edited_by_users FOREIGN KEY(last_edited_by) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE notes ADD CONSTRAINT fk_notes_author_id_users FOREIGN KEY(author_id) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE editor_articles ADD CONSTRAINT fk_article_district_city FOREIGN KEY(district_id, city_id) REFERENCES districts (id, city_id)"
    )
    op.execute(
        "ALTER TABLE editor_revisions ADD CONSTRAINT fk_editor_revisions_article_id_editor_articles FOREIGN KEY(article_id) REFERENCES editor_articles (id)"
    )
    op.execute(
        "ALTER TABLE audit_logs ADD CONSTRAINT fk_audit_logs_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE events ADD CONSTRAINT fk_events_place_id_places FOREIGN KEY(place_id) REFERENCES places (id)"
    )
    op.execute(
        "ALTER TABLE refresh_tokens ADD CONSTRAINT fk_refresh_tokens_session_id_auth_sessions FOREIGN KEY(session_id) REFERENCES auth_sessions (id)"
    )
    op.execute(
        "ALTER TABLE editor_revision_assets ADD CONSTRAINT fk_editor_revision_assets_asset_id_media_assets FOREIGN KEY(asset_id) REFERENCES media_assets (id)"
    )
    op.execute(
        "ALTER TABLE user_blocks ADD CONSTRAINT fk_user_blocks_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE note_reports ADD CONSTRAINT fk_note_reports_submission_id_note_submissions FOREIGN KEY(submission_id) REFERENCES note_submissions (id)"
    )
    op.execute(
        "ALTER TABLE note_reports ADD CONSTRAINT fk_report_note_submission FOREIGN KEY(submission_id, note_id) REFERENCES note_submissions (id, note_id)"
    )
    op.execute(
        "ALTER TABLE editor_article_reports ADD CONSTRAINT fk_editor_article_reports_article_id_editor_articles FOREIGN KEY(article_id) REFERENCES editor_articles (id)"
    )
    op.execute(
        "ALTER TABLE notes ADD CONSTRAINT fk_notes_city_id_cities FOREIGN KEY(city_id) REFERENCES cities (id)"
    )
    op.execute(
        "ALTER TABLE editor_article_reactions ADD CONSTRAINT fk_editor_article_reactions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE editor_revisions ADD CONSTRAINT fk_editor_revisions_primary_place_id_places FOREIGN KEY(primary_place_id) REFERENCES places (id)"
    )
    op.execute(
        "ALTER TABLE editor_article_reports ADD CONSTRAINT fk_editor_article_reports_revision_id_editor_revisions FOREIGN KEY(revision_id) REFERENCES editor_revisions (id)"
    )
    op.execute(
        "ALTER TABLE auth_sessions ADD CONSTRAINT fk_auth_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE note_drafts ADD CONSTRAINT fk_note_drafts_note_id_notes FOREIGN KEY(note_id) REFERENCES notes (id)"
    )
    op.execute(
        "ALTER TABLE note_submissions ADD CONSTRAINT fk_note_submissions_note_id_notes FOREIGN KEY(note_id) REFERENCES notes (id)"
    )
    op.execute(
        "ALTER TABLE user_blocks ADD CONSTRAINT fk_user_blocks_blocked_user_id_users FOREIGN KEY(blocked_user_id) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE note_reports ADD CONSTRAINT fk_note_reports_resolved_by_users FOREIGN KEY(resolved_by) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE notes ADD CONSTRAINT fk_notes_place_id_places FOREIGN KEY(place_id) REFERENCES places (id)"
    )
    op.execute(
        "ALTER TABLE editor_reviews ADD CONSTRAINT fk_editor_reviews_revision_id_editor_revisions FOREIGN KEY(revision_id) REFERENCES editor_revisions (id)"
    )
    op.execute(
        "ALTER TABLE editor_article_reactions ADD CONSTRAINT fk_editor_article_reactions_article_id_editor_articles FOREIGN KEY(article_id) REFERENCES editor_articles (id)"
    )
    op.execute(
        "ALTER TABLE event_sessions ADD CONSTRAINT fk_event_sessions_event_id_events FOREIGN KEY(event_id) REFERENCES events (id)"
    )
    op.execute(
        "ALTER TABLE editor_revisions ADD CONSTRAINT fk_editor_revisions_primary_event_id_events FOREIGN KEY(primary_event_id) REFERENCES events (id)"
    )
    op.execute(
        "ALTER TABLE editor_article_reports ADD CONSTRAINT fk_editor_article_reports_resolved_by_users FOREIGN KEY(resolved_by) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE editor_articles ADD CONSTRAINT fk_editor_articles_author_id_users FOREIGN KEY(author_id) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE editor_revisions ADD CONSTRAINT fk_editor_revisions_cover_asset_id_media_assets FOREIGN KEY(cover_asset_id) REFERENCES media_assets (id)"
    )
    op.execute(
        "ALTER TABLE note_drafts ADD CONSTRAINT fk_note_drafts_place_id_places FOREIGN KEY(place_id) REFERENCES places (id)"
    )
    op.execute(
        "ALTER TABLE note_submissions ADD CONSTRAINT fk_note_submissions_place_id_places FOREIGN KEY(place_id) REFERENCES places (id)"
    )
    op.execute(
        "ALTER TABLE notes ADD CONSTRAINT fk_notes_event_id_events FOREIGN KEY(event_id) REFERENCES events (id)"
    )
    op.execute(
        "ALTER TABLE editor_reviews ADD CONSTRAINT fk_editor_reviews_reviewer_id_users FOREIGN KEY(reviewer_id) REFERENCES users (id)"
    )
    op.execute(
        "ALTER TABLE editor_articles ADD CONSTRAINT fk_article_own_revision FOREIGN KEY(published_revision_id, id) REFERENCES editor_revisions (id, article_id)"
    )
    op.execute(
        "ALTER TABLE user_roles ADD CONSTRAINT fk_user_roles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)"
    )


def downgrade():
    op.execute("ALTER TABLE editor_articles DROP FOREIGN KEY fk_editor_articles_city_id_cities")
    op.execute("ALTER TABLE districts DROP FOREIGN KEY fk_districts_city_id_cities")
    op.execute("ALTER TABLE refresh_tokens DROP FOREIGN KEY fk_refresh_tokens_parent_id_refresh_tokens")
    op.execute("ALTER TABLE places DROP FOREIGN KEY fk_place_district_city")
    op.execute("ALTER TABLE note_drafts DROP FOREIGN KEY fk_note_drafts_event_id_events")
    op.execute("ALTER TABLE note_submissions DROP FOREIGN KEY fk_note_submissions_event_id_events")
    op.execute("ALTER TABLE editor_article_reports DROP FOREIGN KEY fk_report_article_revision")
    op.execute("ALTER TABLE editor_revisions DROP FOREIGN KEY fk_editor_revisions_submitted_by_users")
    op.execute("ALTER TABLE place_assets DROP FOREIGN KEY fk_place_assets_place_id_places")
    op.execute("ALTER TABLE editor_articles DROP FOREIGN KEY fk_editor_articles_district_id_districts")
    op.execute("ALTER TABLE editor_drafts DROP FOREIGN KEY fk_editor_drafts_article_id_editor_articles")
    op.execute("ALTER TABLE user_roles DROP FOREIGN KEY fk_user_roles_granted_by_users")
    op.execute("ALTER TABLE note_submissions DROP FOREIGN KEY fk_note_submissions_reviewer_id_users")
    op.execute("ALTER TABLE places DROP FOREIGN KEY fk_places_cover_asset_id_media_assets")
    op.execute("ALTER TABLE place_assets DROP FOREIGN KEY fk_place_assets_asset_id_media_assets")
    op.execute("ALTER TABLE users DROP FOREIGN KEY fk_users_city_id_cities")
    op.execute("ALTER TABLE events DROP FOREIGN KEY fk_event_place_city")
    op.execute("ALTER TABLE editor_drafts DROP FOREIGN KEY fk_editor_drafts_primary_place_id_places")
    op.execute(
        "ALTER TABLE editor_revision_tags DROP FOREIGN KEY fk_editor_revision_tags_revision_id_editor_revisions"
    )
    op.execute("ALTER TABLE note_images DROP FOREIGN KEY fk_note_images_note_id_notes")
    op.execute("ALTER TABLE event_participations DROP FOREIGN KEY fk_event_participations_user_id_users")
    op.execute("ALTER TABLE notes DROP FOREIGN KEY fk_note_own_submission")
    op.execute("ALTER TABLE editor_drafts DROP FOREIGN KEY fk_editor_drafts_primary_event_id_events")
    op.execute("ALTER TABLE event_participations DROP FOREIGN KEY fk_participation_session_event")
    op.execute("ALTER TABLE editor_revision_tags DROP FOREIGN KEY fk_editor_revision_tags_tag_id_tags")
    op.execute("ALTER TABLE note_images DROP FOREIGN KEY fk_note_images_asset_id_media_assets")
    op.execute("ALTER TABLE event_participations DROP FOREIGN KEY fk_event_participations_event_id_events")
    op.execute("ALTER TABLE places DROP FOREIGN KEY fk_places_city_id_cities")
    op.execute("ALTER TABLE idempotency_records DROP FOREIGN KEY fk_idempotency_records_user_id_users")
    op.execute("ALTER TABLE note_reactions DROP FOREIGN KEY fk_note_reactions_user_id_users")
    op.execute("ALTER TABLE note_reports DROP FOREIGN KEY fk_note_reports_reporter_id_users")
    op.execute("ALTER TABLE users DROP FOREIGN KEY fk_users_avatar_asset_id_media_assets")
    op.execute("ALTER TABLE editor_drafts DROP FOREIGN KEY fk_editor_drafts_cover_asset_id_media_assets")
    op.execute("ALTER TABLE media_assets DROP FOREIGN KEY fk_media_assets_owner_id_users")
    op.execute(
        "ALTER TABLE event_participations DROP FOREIGN KEY fk_event_participations_session_id_event_sessions"
    )
    op.execute("ALTER TABLE places DROP FOREIGN KEY fk_places_district_id_districts")
    op.execute("ALTER TABLE events DROP FOREIGN KEY fk_events_city_id_cities")
    op.execute(
        "ALTER TABLE editor_revision_assets DROP FOREIGN KEY fk_editor_revision_assets_revision_id_editor_revisions"
    )
    op.execute("ALTER TABLE note_reactions DROP FOREIGN KEY fk_note_reactions_note_id_notes")
    op.execute("ALTER TABLE note_reports DROP FOREIGN KEY fk_note_reports_note_id_notes")
    op.execute(
        "ALTER TABLE editor_article_reports DROP FOREIGN KEY fk_editor_article_reports_reporter_id_users"
    )
    op.execute("ALTER TABLE editor_drafts DROP FOREIGN KEY fk_editor_drafts_last_edited_by_users")
    op.execute("ALTER TABLE notes DROP FOREIGN KEY fk_notes_author_id_users")
    op.execute("ALTER TABLE editor_articles DROP FOREIGN KEY fk_article_district_city")
    op.execute("ALTER TABLE editor_revisions DROP FOREIGN KEY fk_editor_revisions_article_id_editor_articles")
    op.execute("ALTER TABLE audit_logs DROP FOREIGN KEY fk_audit_logs_actor_id_users")
    op.execute("ALTER TABLE events DROP FOREIGN KEY fk_events_place_id_places")
    op.execute("ALTER TABLE refresh_tokens DROP FOREIGN KEY fk_refresh_tokens_session_id_auth_sessions")
    op.execute(
        "ALTER TABLE editor_revision_assets DROP FOREIGN KEY fk_editor_revision_assets_asset_id_media_assets"
    )
    op.execute("ALTER TABLE user_blocks DROP FOREIGN KEY fk_user_blocks_user_id_users")
    op.execute("ALTER TABLE note_reports DROP FOREIGN KEY fk_note_reports_submission_id_note_submissions")
    op.execute("ALTER TABLE note_reports DROP FOREIGN KEY fk_report_note_submission")
    op.execute(
        "ALTER TABLE editor_article_reports DROP FOREIGN KEY fk_editor_article_reports_article_id_editor_articles"
    )
    op.execute("ALTER TABLE notes DROP FOREIGN KEY fk_notes_city_id_cities")
    op.execute(
        "ALTER TABLE editor_article_reactions DROP FOREIGN KEY fk_editor_article_reactions_user_id_users"
    )
    op.execute("ALTER TABLE editor_revisions DROP FOREIGN KEY fk_editor_revisions_primary_place_id_places")
    op.execute(
        "ALTER TABLE editor_article_reports DROP FOREIGN KEY fk_editor_article_reports_revision_id_editor_revisions"
    )
    op.execute("ALTER TABLE auth_sessions DROP FOREIGN KEY fk_auth_sessions_user_id_users")
    op.execute("ALTER TABLE note_drafts DROP FOREIGN KEY fk_note_drafts_note_id_notes")
    op.execute("ALTER TABLE note_submissions DROP FOREIGN KEY fk_note_submissions_note_id_notes")
    op.execute("ALTER TABLE user_blocks DROP FOREIGN KEY fk_user_blocks_blocked_user_id_users")
    op.execute("ALTER TABLE note_reports DROP FOREIGN KEY fk_note_reports_resolved_by_users")
    op.execute("ALTER TABLE notes DROP FOREIGN KEY fk_notes_place_id_places")
    op.execute("ALTER TABLE editor_reviews DROP FOREIGN KEY fk_editor_reviews_revision_id_editor_revisions")
    op.execute(
        "ALTER TABLE editor_article_reactions DROP FOREIGN KEY fk_editor_article_reactions_article_id_editor_articles"
    )
    op.execute("ALTER TABLE event_sessions DROP FOREIGN KEY fk_event_sessions_event_id_events")
    op.execute("ALTER TABLE editor_revisions DROP FOREIGN KEY fk_editor_revisions_primary_event_id_events")
    op.execute(
        "ALTER TABLE editor_article_reports DROP FOREIGN KEY fk_editor_article_reports_resolved_by_users"
    )
    op.execute("ALTER TABLE editor_articles DROP FOREIGN KEY fk_editor_articles_author_id_users")
    op.execute(
        "ALTER TABLE editor_revisions DROP FOREIGN KEY fk_editor_revisions_cover_asset_id_media_assets"
    )
    op.execute("ALTER TABLE note_drafts DROP FOREIGN KEY fk_note_drafts_place_id_places")
    op.execute("ALTER TABLE note_submissions DROP FOREIGN KEY fk_note_submissions_place_id_places")
    op.execute("ALTER TABLE notes DROP FOREIGN KEY fk_notes_event_id_events")
    op.execute("ALTER TABLE editor_reviews DROP FOREIGN KEY fk_editor_reviews_reviewer_id_users")
    op.execute("ALTER TABLE editor_articles DROP FOREIGN KEY fk_article_own_revision")
    op.execute("ALTER TABLE user_roles DROP FOREIGN KEY fk_user_roles_user_id_users")
    op.execute("DROP TABLE audit_logs")
    op.execute("DROP TABLE idempotency_records")
    op.execute("DROP TABLE jobs")
    op.execute("DROP TABLE editor_article_reports")
    op.execute("DROP TABLE note_reports")
    op.execute("DROP TABLE user_blocks")
    op.execute("DROP TABLE event_participations")
    op.execute("DROP TABLE editor_article_reactions")
    op.execute("DROP TABLE note_reactions")
    op.execute("DROP TABLE note_submissions")
    op.execute("DROP TABLE note_drafts")
    op.execute("DROP TABLE note_images")
    op.execute("DROP TABLE notes")
    op.execute("DROP TABLE editor_reviews")
    op.execute("DROP TABLE editor_revision_assets")
    op.execute("DROP TABLE editor_revision_tags")
    op.execute("DROP TABLE editor_revisions")
    op.execute("DROP TABLE editor_drafts")
    op.execute("DROP TABLE editor_articles")
    op.execute("DROP TABLE media_assets")
    op.execute("DROP TABLE tags")
    op.execute("DROP TABLE event_sessions")
    op.execute("DROP TABLE events")
    op.execute("DROP TABLE place_assets")
    op.execute("DROP TABLE places")
    op.execute("DROP TABLE districts")
    op.execute("DROP TABLE cities")
    op.execute("DROP TABLE refresh_tokens")
    op.execute("DROP TABLE auth_sessions")
    op.execute("DROP TABLE auth_challenges")
    op.execute("DROP TABLE auth_send_limits")
    op.execute("DROP TABLE user_roles")
    op.execute("DROP TABLE users")
