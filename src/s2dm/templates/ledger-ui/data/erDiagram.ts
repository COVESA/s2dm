// The documented ModL ledger shape, kept deliberately smaller than the model in
// modlProfile.ts: the two self-referencing relationships and the two concepts
// columns they involve are left out, because mermaid draws a self reference as a
// loop that obscures the four-level chain this diagram exists to show.
export const LEDGER_ER_DIAGRAM = `erDiagram
    concepts ||--o{ revisions : "tracked by"
    concepts ||--o{ contracts : "realized as"
    revisions ||--o{ contracts : "triggers"
    contracts ||--o{ bindings : "expanded into"

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
        string instance_label
        string status
    }
`;
