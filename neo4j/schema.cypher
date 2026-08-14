CREATE CONSTRAINT person_id_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.person_id IS UNIQUE;

CREATE CONSTRAINT account_id_unique IF NOT EXISTS
FOR (a:Account) REQUIRE a.account_id IS UNIQUE;

CREATE CONSTRAINT bank_id_unique IF NOT EXISTS
FOR (b:Bank) REQUIRE b.bank_id IS UNIQUE;

CREATE CONSTRAINT ip_address_unique IF NOT EXISTS
FOR (i:IPAddress) REQUIRE i.address IS UNIQUE;

CREATE CONSTRAINT txn_id_unique IF NOT EXISTS
FOR ()-[t:TRANSFERRED_TO]-() REQUIRE t.transaction_id IS UNIQUE;

CREATE INDEX account_balance_idx IF NOT EXISTS
FOR (a:Account) ON (a.balance);

CREATE INDEX transferred_amount_idx IF NOT EXISTS
FOR ()-[t:TRANSFERRED_TO]-() ON (t.amount);

CREATE INDEX transferred_timestamp_idx IF NOT EXISTS
FOR ()-[t:TRANSFERRED_TO]-() ON (t.timestamp);