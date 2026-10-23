-- LiveBridge Local - cole este Script em ServerScriptService.
-- O jogo consulta o servidor Python e transforma eventos TikTok em avatares.

local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")

local URL = "http://127.0.0.1:5000/eventos"
local cursor = 0
local pasta = workspace:FindFirstChild("LiveAvatars") or Instance.new("Folder")
pasta.Name = "LiveAvatars"
pasta.Parent = workspace

local function spawnAvatar(userId, name, scale)
    if not userId or tonumber(userId) == 0 then
        local p = Instance.new("Part")
        p.Name = name ~= "" and name or "TikTok"
        p.Size = Vector3.new(2, 2, 2) * math.clamp(scale or 1, 0.5, 6)
        p.Anchored = true
        p.Position = Vector3.new(math.random(-20,20), 3, math.random(-10,10))
        p.Parent = pasta
        task.delay(30, function() if p.Parent then p:Destroy() end end)
        return
    end

    local ok, desc = pcall(function()
        return Players:GetHumanoidDescriptionFromUserIdAsync(tonumber(userId))
    end)
    if not ok then
        warn("LiveBridge: nao foi possivel carregar avatar", userId, desc)
        return
    end

    local ok2, model = pcall(function()
        return Players:CreateHumanoidModelFromDescription(desc, Enum.HumanoidRigType.R15)
    end)
    if not ok2 or not model then
        warn("LiveBridge: falha ao criar avatar", model)
        return
    end

    model.Name = name ~= "" and name or ("User_" .. tostring(userId))
    model.Parent = pasta
    local root = model:FindFirstChild("HumanoidRootPart")
    if root then
        root.CFrame = CFrame.new(math.random(-20,20), 3, math.random(-10,10))
    end
    local s = math.clamp(scale or 1, 0.5, 6)
    pcall(function() model:ScaleTo(s) end)
    task.delay(45, function() if model.Parent then model:Destroy() end end)
end

local function process(event)
    if event.type == "gift" or event.type == "comment" then
        local count = math.clamp(tonumber(event.count) or 1, 1, 20)
        for _ = 1, count do
            spawnAvatar(event.robloxUserId, event.robloxName or event.nickname or event.user or "TikTok", tonumber(event.scale) or 1)
            task.wait(0.15)
        end
    end
end

while true do
    local ok, response = pcall(function()
        return HttpService:GetAsync(URL .. "?after=" .. tostring(cursor))
    end)
    if ok then
        local decodedOk, data = pcall(function() return HttpService:JSONDecode(response) end)
        if decodedOk and data and data.events then
            for _, event in ipairs(data.events) do
                cursor = math.max(cursor, tonumber(event.id) or cursor)
                task.spawn(process, event)
            end
        end
    else
        warn("LiveBridge: servidor Python nao respondeu: ", response)
    end
    task.wait(0.5)
end
