"use client";

import { SparklesIcon } from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import {
  Item,
  ItemActions,
  ItemTitle,
  ItemContent,
  ItemDescription,
} from "@/components/ui/item";
import { Switch } from "@/components/ui/switch";
import { useI18n } from "@/core/i18n/hooks";
import { useEnableSkill, useSkills } from "@/core/skills/hooks";
import type { Skill } from "@/core/skills/type";
import { env } from "@/env";

import { SettingsSection } from "./settings-section";

export function SkillSettingsPage() {
  const { t } = useI18n();
  const { skills, isLoading, error } = useSkills();
  return (
    <SettingsSection
      title={t.settings.skills.title}
      description={t.settings.skills.description}
    >
      {isLoading ? (
        <div className="text-muted-foreground text-sm">{t.common.loading}</div>
      ) : error ? (
        <div>Error: {error.message}</div>
      ) : (
        <SkillSettingsList skills={skills} />
      )}
    </SettingsSection>
  );
}

function SkillSettingsList({ skills }: { skills: Skill[] }) {
  const { t } = useI18n();
  const [filter, setFilter] = useState<"public" | "custom">("public");
  const { mutate: enableSkill } = useEnableSkill();
  const filteredSkills = useMemo(
    () => skills.filter((skill) => skill.category === filter),
    [skills, filter],
  );
  if (skills.length === 0) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <SparklesIcon />
          </EmptyMedia>
          <EmptyTitle>No agent skill yet</EmptyTitle>
          <EmptyDescription>
            Put your agent skill folders under the `/skills/custom` folder under
            the root folder of DeerFlow.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }
  return (
    <div className="flex w-full flex-col gap-4">
      <header className="flex gap-2">
        <Button
          className="rounded-xl"
          size="sm"
          variant={filter === "public" ? "default" : "outline"}
          onClick={() => setFilter("public")}
        >
          {t.common.public}
        </Button>
        <Button
          className="rounded-xl"
          size="sm"
          variant={filter === "custom" ? "default" : "outline"}
          onClick={() => setFilter("custom")}
        >
          {t.common.custom}
        </Button>
      </header>
      {filteredSkills.length === 0 && (
        <Empty>
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <SparklesIcon />
            </EmptyMedia>
            <EmptyTitle>No skill yet</EmptyTitle>
            <EmptyDescription>
              Put your skill folders under the `skills/{filter}` folder under
              the root folder of DeerFlow.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      )}
      {filteredSkills.length > 0 &&
        filteredSkills.map((skill) => (
          <Item className="w-full" variant="outline" key={skill.name}>
            <ItemContent>
              <ItemTitle>
                <div className="flex items-center gap-2">{skill.name}</div>
              </ItemTitle>
              <ItemDescription className="line-clamp-4">
                {skill.description}
              </ItemDescription>
            </ItemContent>
            <ItemActions>
              <Switch
                checked={skill.enabled}
                disabled={env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true"}
                onCheckedChange={(checked) =>
                  enableSkill({ skillName: skill.name, enabled: checked })
                }
              />
            </ItemActions>
          </Item>
        ))}
    </div>
  );
}
