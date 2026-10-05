import { Anchor, Button, Code, CopyButton, Group, List, Stack, Tabs, Text } from "@mantine/core";

/** The address every chatbot connects to. Public: no sign-in, no key. */
const MCP_URL = "https://grzyby.gugnowski.com/mcp";
const CLAUDE_CODE = `claude mcp add --transport http grzyby ${MCP_URL}`;

function Copyable({ value, label }: { value: string; label: string }) {
    return (
        <Group gap="xs" wrap="nowrap" align="center">
            <Code block style={{ flex: 1, overflowX: "auto" }}>
                {value}
            </Code>
            <CopyButton value={value}>
                {({ copied, copy }) => (
                    <Button size="xs" variant="light" color={copied ? "teal" : "indigo"} onClick={copy} aria-label={label}>
                        {copied ? "Skopiowano" : "Kopiuj"}
                    </Button>
                )}
            </CopyButton>
        </Group>
    );
}

/** How to add the server to each chatbot: one tab per client. Menu names as the apps show them
 *  (ChatGPT's mostly in English); checked against their help pages on 5.10.2026. */
export function InstallGuide() {
    return (
        <Tabs defaultValue="claude" keepMounted={false}>
            <Tabs.List>
                <Tabs.Tab value="claude">Claude (web i aplikacja)</Tabs.Tab>
                <Tabs.Tab value="chatgpt">ChatGPT</Tabs.Tab>
                <Tabs.Tab value="claude-code">Claude Code</Tabs.Tab>
            </Tabs.List>

            <Tabs.Panel value="claude" pt="md">
                <Stack gap="sm">
                    <Text>Na claude.ai i w aplikacji na komputer — tak samo. Konektor dodany raz działa też w aplikacji na telefon.</Text>
                    <List type="ordered" spacing="xs">
                        <List.Item>
                            <b>Ustawienia</b> → <b>Konektory</b> (Connectors) —{" "}
                            <Anchor href="https://claude.ai/settings/connectors" target="_blank" rel="noreferrer">
                                claude.ai/settings/connectors
                            </Anchor>
                            .
                        </List.Item>
                        <List.Item>
                            <b>Dodaj własny konektor</b> (Add custom connector).
                        </List.Item>
                        <List.Item>
                            Nazwa: <b>Gdzie na grzyby</b>, adres:
                            <Copyable value={MCP_URL} label="Kopiuj adres dla Claude" />
                            Bez logowania i bez klucza — pozostałe pola zostaw puste. <b>Dodaj</b>.
                        </List.Item>
                        <List.Item>
                            W nowej rozmowie otwórz menu narzędzi pod polem wiadomości (<b>+</b>) i włącz <b>Gdzie na grzyby</b>.
                        </List.Item>
                        <List.Item>Zapytaj, np. „Gdzie dziś na podgrzybki koło Olsztyna?” — odpowiedź przyjdzie z mapą.</List.Item>
                    </List>
                </Stack>
            </Tabs.Panel>

            <Tabs.Panel value="chatgpt" pt="md">
                <Stack gap="sm">
                    <Text>
                        Na chatgpt.com, w planie płatnym (Plus, Pro, Business). Własne serwery MCP działają w trybie dewelopera — to
                        ustawienie OpenAI, nie nasze.
                    </Text>
                    <List type="ordered" spacing="xs">
                        <List.Item>
                            Profil → <b>Settings</b> → <b>Security and login</b> → włącz <b>Developer mode</b>. (W starszej wersji: Settings
                            → Apps & Connectors → Advanced settings.)
                        </List.Item>
                        <List.Item>
                            W menu bocznym <b>Plugins</b> (
                            <Anchor href="https://chatgpt.com/plugins" target="_blank" rel="noreferrer">
                                chatgpt.com/plugins
                            </Anchor>
                            ) → <b>+</b> → <b>Create custom MCP server</b>.
                        </List.Item>
                        <List.Item>
                            Nazwa: <b>Gdzie na grzyby</b>, opis: „Gdzie i kiedy na grzyby w Polsce, z mapą”. W <b>Connection</b> wklej
                            adres:
                            <Copyable value={MCP_URL} label="Kopiuj adres dla ChatGPT" />
                            Uwierzytelnianie: <b>No authentication</b>. Potwierdź <b>I understand and want to continue</b> i utwórz.
                        </List.Item>
                        <List.Item>
                            W nowej rozmowie wpisz <b>@</b> i wybierz <b>Gdzie na grzyby</b> (albo <b>+</b> → Developer mode), potem zapytaj
                            o grzyby.
                        </List.Item>
                    </List>
                    <Text size="sm" c="dimmed">
                        Po naszej aktualizacji, gdy mapa wygląda po staremu: Plugins → Gdzie na grzyby → <b>Refresh</b>.
                    </Text>
                </Stack>
            </Tabs.Panel>

            <Tabs.Panel value="claude-code" pt="md">
                <Stack gap="sm">
                    <Text>W terminalu, jedną komendą (Claude Code pokazuje odpowiedź tekstem, bez mapy):</Text>
                    <Copyable value={CLAUDE_CODE} label="Kopiuj komendę dla Claude Code" />
                    <Text>
                        Potem w Claude Code zapytaj o grzyby; <Code>/mcp</Code> pokazuje, czy serwer jest podłączony.
                    </Text>
                </Stack>
            </Tabs.Panel>
        </Tabs>
    );
}
