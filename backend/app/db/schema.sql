-- HSE campaign store for /tool. PostgreSQL on the same machine as the API.
-- The API is the only client. Do not point this at a managed database.
--
-- Anonymity: invitations hold the email and the link token.
-- hse_responses does not. There is no foreign key from an answer to an invitation,
-- and the answer has no email, token, or client address.
-- company_id and round_id are the shared wave, not a person.
-- Demographics are one JSON object so the field list can still change.
-- Blocked keys are identifiers we already refused, not the allowed list.

CREATE TABLE IF NOT EXISTS companies (
    id uuid PRIMARY KEY,
    slug text NOT NULL UNIQUE,
    name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS company_rounds (
    id uuid PRIMARY KEY,
    company_id uuid NOT NULL REFERENCES companies (id),
    label text NOT NULL,
    opened_on date NOT NULL,
    closed_on date,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (company_id, label)
);

CREATE UNIQUE INDEX IF NOT EXISTS company_rounds_one_open
    ON company_rounds (company_id)
    WHERE closed_on IS NULL;

CREATE TABLE IF NOT EXISTS invitation_uploads (
    id uuid PRIMARY KEY,
    company_id uuid NOT NULL REFERENCES companies (id),
    round_id uuid NOT NULL REFERENCES company_rounds (id),
    source_name text NOT NULL,
    format text NOT NULL CHECK (format IN ('json', 'csv', 'xlsx')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS invitations (
    id uuid PRIMARY KEY,
    company_id uuid NOT NULL REFERENCES companies (id),
    round_id uuid NOT NULL REFERENCES company_rounds (id),
    upload_id uuid NOT NULL REFERENCES invitation_uploads (id),
    email text NOT NULL,
    link_token text NOT NULL,
    link_token_hash text NOT NULL UNIQUE,
    status text NOT NULL CHECK (status IN ('pending', 'submitted')),
    submitted_at timestamptz,
    sent_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (round_id, email),
    CONSTRAINT invitations_submitted_pair CHECK (
        (status = 'pending' AND submitted_at IS NULL)
        OR (status = 'submitted' AND submitted_at IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS invitations_round_status
    ON invitations (round_id, status);

-- Raw marks in official item order (i01 is item 1). Not reverse-scored.
-- submitted_on is a day, not a copy of invitations.submitted_at.
CREATE TABLE IF NOT EXISTS hse_responses (
    id uuid PRIMARY KEY,
    company_id uuid NOT NULL REFERENCES companies (id),
    round_id uuid NOT NULL REFERENCES company_rounds (id),
    submitted_on date NOT NULL,
    demographics jsonb NOT NULL DEFAULT '{}'::jsonb,
    i01 smallint NOT NULL,
    i02 smallint NOT NULL,
    i03 smallint NOT NULL,
    i04 smallint NOT NULL,
    i05 smallint NOT NULL,
    i06 smallint NOT NULL,
    i07 smallint NOT NULL,
    i08 smallint NOT NULL,
    i09 smallint NOT NULL,
    i10 smallint NOT NULL,
    i11 smallint NOT NULL,
    i12 smallint NOT NULL,
    i13 smallint NOT NULL,
    i14 smallint NOT NULL,
    i15 smallint NOT NULL,
    i16 smallint NOT NULL,
    i17 smallint NOT NULL,
    i18 smallint NOT NULL,
    i19 smallint NOT NULL,
    i20 smallint NOT NULL,
    i21 smallint NOT NULL,
    i22 smallint NOT NULL,
    i23 smallint NOT NULL,
    i24 smallint NOT NULL,
    i25 smallint NOT NULL,
    i26 smallint NOT NULL,
    i27 smallint NOT NULL,
    i28 smallint NOT NULL,
    i29 smallint NOT NULL,
    i30 smallint NOT NULL,
    i31 smallint NOT NULL,
    i32 smallint NOT NULL,
    i33 smallint NOT NULL,
    i34 smallint NOT NULL,
    i35 smallint NOT NULL,
    CONSTRAINT hse_responses_range CHECK (
        i01 BETWEEN 1 AND 5
        AND i02 BETWEEN 1 AND 5
        AND i03 BETWEEN 1 AND 5
        AND i04 BETWEEN 1 AND 5
        AND i05 BETWEEN 1 AND 5
        AND i06 BETWEEN 1 AND 5
        AND i07 BETWEEN 1 AND 5
        AND i08 BETWEEN 1 AND 5
        AND i09 BETWEEN 1 AND 5
        AND i10 BETWEEN 1 AND 5
        AND i11 BETWEEN 1 AND 5
        AND i12 BETWEEN 1 AND 5
        AND i13 BETWEEN 1 AND 5
        AND i14 BETWEEN 1 AND 5
        AND i15 BETWEEN 1 AND 5
        AND i16 BETWEEN 1 AND 5
        AND i17 BETWEEN 1 AND 5
        AND i18 BETWEEN 1 AND 5
        AND i19 BETWEEN 1 AND 5
        AND i20 BETWEEN 1 AND 5
        AND i21 BETWEEN 1 AND 5
        AND i22 BETWEEN 1 AND 5
        AND i23 BETWEEN 1 AND 5
        AND i24 BETWEEN 1 AND 5
        AND i25 BETWEEN 1 AND 5
        AND i26 BETWEEN 1 AND 5
        AND i27 BETWEEN 1 AND 5
        AND i28 BETWEEN 1 AND 5
        AND i29 BETWEEN 1 AND 5
        AND i30 BETWEEN 1 AND 5
        AND i31 BETWEEN 1 AND 5
        AND i32 BETWEEN 1 AND 5
        AND i33 BETWEEN 1 AND 5
        AND i34 BETWEEN 1 AND 5
        AND i35 BETWEEN 1 AND 5
    ),
    CONSTRAINT hse_responses_demographics_object CHECK (jsonb_typeof(demographics) = 'object'),
    CONSTRAINT hse_responses_no_direct_identifiers CHECK (
        NOT jsonb_exists_any(
            demographics,
            ARRAY[
                'name',
                'nome',
                'full_name',
                'email',
                'e-mail',
                'mail',
                'job',
                'job_title',
                'jobtitle',
                'cargo',
                'funcao',
                'função',
                'token',
                'link_token',
                'ip',
                'invitation_id',
                'invitation'
            ]
        )
    )
);

CREATE INDEX IF NOT EXISTS hse_responses_round
    ON hse_responses (round_id, submitted_on);

INSERT INTO companies (id, slug, name)
VALUES ('11111111-1111-4111-8111-111111111111', 'pilot', 'Empresa piloto')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO company_rounds (id, company_id, label, opened_on)
SELECT '22222222-2222-4222-8222-222222222222', c.id, 'rodada-1', CURRENT_DATE
FROM companies AS c
WHERE c.slug = 'pilot'
  AND NOT EXISTS (
      SELECT 1
      FROM company_rounds AS r
      WHERE r.company_id = c.id
        AND r.closed_on IS NULL
  );

ALTER TABLE invitations ADD COLUMN IF NOT EXISTS sent_at timestamptz;
