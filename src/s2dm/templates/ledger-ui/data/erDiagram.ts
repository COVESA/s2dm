// The documented ModL ledger shape, kept deliberately smaller than the keys
// that a ModL export declares: the two self-referencing relationships and the
// two concepts columns they involve are left out, because mermaid draws a self
// reference as a loop that obscures the four-level chain this diagram exists to
// show. Of the two keys from contract_references to contracts, only
// contract_uri is drawn.
export const LEDGER_ER_DIAGRAM = `erDiagram
    concepts ||--o{ revisions : "tracked by"
    concepts ||--o{ contracts : "realized as"
    revisions ||--o{ contracts : "triggers"
    revisions ||--o{ revision_aspects : "records changes in"
    contracts ||--o{ bindings : "expanded into"
    contracts ||--o{ contract_references : "depends on"

    concepts {
        int serial PK
        string concept_uri UK
        string current_label
        string previous_labels
        string kind
        string status
    }
    revisions {
        int serial PK
        string revision_uri UK
        string concept_uri FK
        string previous_revision_uri FK
        string status
    }
    contracts {
        int serial PK
        string contract_uri UK
        string concept_uri FK
        string revision_uri FK
        string status
    }
    bindings {
        int serial PK
        string binding_uri UK
        string contract_uri FK
        string instance_tags
        string runtime_path
        string status
    }
    revision_aspects {
        string revision_uri FK
        string aspect_key
        string operation
        string previous_value
        string newer_value
        string reason
    }
    contract_references {
        string contract_uri FK
        string role
        string target_contract_uri FK
    }
`;
