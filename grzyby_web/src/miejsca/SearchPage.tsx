import { Alert, Button, Chip, Container, Group, Paper, Select, SimpleGrid, Stack, Text, TextInput, Title } from "@mantine/core";
import { useEffect, useRef, useState, type SyntheticEvent } from "react";

import { fetchAnswer, type Answer } from "./api";
import { MapWidget } from "./MapWidget";
import { DAYS_AHEAD, dayName, fromSearch, GRZYBY, MAX_SPOTS, RADII, START, toSearch, type Question } from "./question";

type Result = { question: Question; answer: Answer } | { question: Question; error: string };

const SPOTS = [3, 5, 10, MAX_SPOTS];

/** The search without a chatbot: a form and the map, nothing else on the page. The question
 *  lives in the address, so a link to a search opens it already asked. */
export function SearchPage() {
    const [linked] = useState(() => fromSearch(window.location.search));
    const [question, setQuestion] = useState<Question>(linked ?? START);
    const [asked, setAsked] = useState<Question | null>(linked);
    const [result, setResult] = useState<Result | null>(null);
    const loading = asked !== null && result?.question !== asked;
    const below = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!asked) return;
        // StrictMode runs effects twice in development: abort the first request, ignore its result.
        const controller = new AbortController();
        fetchAnswer(asked, controller.signal)
            .then((answer) => {
                setResult({ question: asked, answer });
            })
            .catch((e: unknown) => {
                if (!controller.signal.aborted) setResult({ question: asked, error: e instanceof Error ? e.message : String(e) });
            });
        return () => {
            controller.abort();
        };
    }, [asked]);

    // The answer comes under the form — on a phone, below the screen: bring it into view.
    useEffect(() => {
        if (result) below.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, [result]);

    const set = <K extends keyof Question>(key: K, value: Question[K]) => {
        setQuestion((q) => ({ ...q, [key]: value }));
    };
    const ready = question.miejscowosc.trim().length >= 2 && question.grzyby.length > 0;

    function submit(event: SyntheticEvent) {
        event.preventDefault();
        if (!ready) return;
        const next = { ...question, miejscowosc: question.miejscowosc.trim() };
        window.history.replaceState(null, "", `?${toSearch(next)}`);
        setAsked(next);
    }

    return (
        <Container size="lg" px="xs" py={{ base: "xs", sm: "lg" }}>
            <Stack gap="md">
                <Paper bg="var(--grzyby-paper)" c="var(--grzyby-ink)" radius="lg" shadow="xl" p={{ base: "md", sm: "lg" }}>
                    <form onSubmit={submit}>
                        <Stack gap="md">
                            <Title order={1} fz={{ base: 26, sm: 32 }} c="moss.9">
                                Gdzie na grzyby
                            </Title>
                            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                                <TextInput
                                    label="Miejscowość"
                                    placeholder="np. Suwałki"
                                    value={question.miejscowosc}
                                    onChange={(e) => {
                                        set("miejscowosc", e.currentTarget.value);
                                    }}
                                    size="md"
                                />
                                <Stack gap={6}>
                                    <Text size="md" fw={500}>
                                        Grzyby
                                    </Text>
                                    <Chip.Group
                                        multiple
                                        value={question.grzyby}
                                        onChange={(value) => {
                                            set("grzyby", value);
                                        }}
                                    >
                                        <Group gap={6}>
                                            {Object.entries(GRZYBY).map(([key, name]) => (
                                                <Chip key={key} value={key} color="moss" variant="light">
                                                    {name}
                                                </Chip>
                                            ))}
                                        </Group>
                                    </Chip.Group>
                                </Stack>
                            </SimpleGrid>
                            <SimpleGrid cols={{ base: 3 }} spacing="sm">
                                <Select
                                    label="Promień"
                                    data={RADII.map((km) => ({ value: String(km), label: `${String(km)} km` }))}
                                    value={String(question.promien_km)}
                                    onChange={(value) => {
                                        if (value) set("promien_km", Number(value));
                                    }}
                                    allowDeselect={false}
                                />
                                <Select
                                    label="Dzień"
                                    data={Array.from({ length: DAYS_AHEAD + 1 }, (_, d) => ({ value: String(d), label: dayName(d) }))}
                                    value={String(question.za_ile_dni)}
                                    onChange={(value) => {
                                        if (value) set("za_ile_dni", Number(value));
                                    }}
                                    allowDeselect={false}
                                />
                                <Select
                                    label="Miejsca"
                                    data={SPOTS.map((n) => String(n))}
                                    value={String(question.ile_miejsc)}
                                    onChange={(value) => {
                                        if (value) set("ile_miejsc", Number(value));
                                    }}
                                    allowDeselect={false}
                                />
                            </SimpleGrid>
                            <Group justify="space-between" align="center" gap="sm">
                                <Text size="sm" c="dimmed">
                                    Nowa okolica: kilka sekund, bo dane o lasach dopiero przychodzą.
                                </Text>
                                <Button type="submit" size="md" loading={loading} disabled={!ready}>
                                    Szukaj
                                </Button>
                            </Group>
                        </Stack>
                    </form>
                </Paper>
                <div ref={below} />
                {result && "error" in result && (
                    <Alert color="red" variant="filled" radius="lg" title="Nie udało się">
                        {result.error}
                    </Alert>
                )}
                {result && "answer" in result && (
                    <Paper radius="lg" shadow="xl" style={{ overflow: "hidden" }} bg="white">
                        <MapWidget key={toSearch(result.question)} answer={result.answer} />
                    </Paper>
                )}
            </Stack>
        </Container>
    );
}
