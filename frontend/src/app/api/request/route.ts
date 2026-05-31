import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/app/api/auth/[...nextauth]/route";
import { createProject, createAgentResponse } from "@/lib/db";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
    const session = await getServerSession(authOptions);

    if (!session || !session.user?.id) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    try {
        const { idea, title } = await req.json();
        const projectTitle = title || idea;

        if (!projectTitle) {
            return NextResponse.json({ error: "Idea or title is required" }, { status: 400 });
        }

        // 1. Create Project
        const project = await createProject(session.user.id, projectTitle);

        if (!project) {
            return NextResponse.json({ error: "Failed to create project" }, { status: 500 });
        }

        // 2. Trigger Agent
        const agentUrl = `${BACKEND_URL}/generate_product`;
        const userApiKey = req.headers.get("X-User-Api-Key");
        const headers: Record<string, string> = {
            "Content-Type": "application/json",
            "X-Project-Id": project.id,
        };
        if (userApiKey) {
            headers["X-User-Api-Key"] = userApiKey;
        }

        const agentResponse = await fetch(agentUrl, {
            method: "POST",
            headers,
            body: JSON.stringify({ requirements: projectTitle }),
        });

        if (!agentResponse.ok) {
            console.error("Agent request failed:", await agentResponse.text());
            // We still return the project, but maybe with a warning or error about the agent
            return NextResponse.json({
                project,
                warning: "Project created but failed to trigger initial analysis."
            }, { status: 201 });
        }

        const agentData = await agentResponse.json();

        // 3. Store Agent Response
        // Note: The proxy route does this, but since we are bypassing the proxy, we do it here.
        // Ideally, the backend should handle storage, or we use a shared service.
        // For now, we replicate the logic.
        await createAgentResponse(project.id, "PRODUCT", JSON.stringify(agentData));

        return NextResponse.json({
            project,
            agentResponse: agentData
        }, { status: 201 });

    } catch (error) {
        console.error("Error in request API:", error);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    }
}
