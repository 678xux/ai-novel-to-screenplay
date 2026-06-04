export const SCRIPT_SCHEMA_VERSION = "1.0.0";

export const screenplaySchema = {
  script: {
    schema_version: "string",
    title: "string",
    source: {
      type: "novel",
      chapter_count: "number",
      input_language: "string",
      adaptation_mode: "string"
    },
    logline: "string",
    themes: ["string"],
    characters: [
      {
        id: "string",
        name: "string",
        role: "string",
        traits: ["string"],
        first_appearance: "string"
      }
    ],
    acts: [
      {
        id: "string",
        title: "string",
        source_chapters: ["string"],
        purpose: "string",
        scenes: [
          {
            id: "string",
            title: "string",
            source_chapter: "string",
            location: "string",
            time: "string",
            mood: "string",
            summary: "string",
            beats: [
              {
                id: "string",
                type: "action | dialogue | narration | transition",
                speaker: "string?",
                text: "string",
                emotion: "string?",
                camera: "string?"
              }
            ],
            conflict: "string",
            turning_point: "string",
            props: ["string"],
            notes: ["string"]
          }
        ]
      }
    ],
    production_notes: {
      estimated_runtime_minutes: "number",
      adaptation_warnings: ["string"],
      revision_suggestions: ["string"]
    }
  }
};
