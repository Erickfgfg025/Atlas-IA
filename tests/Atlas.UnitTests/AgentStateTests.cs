using Atlas.Domain.Agent;

namespace Atlas.UnitTests;

public sealed class AgentStateTests
{
    [Theory]
    [InlineData(AgentState.Standby)]
    [InlineData(AgentState.Listening)]
    [InlineData(AgentState.Thinking)]
    [InlineData(AgentState.Executing)]
    [InlineData(AgentState.Speaking)]
    [InlineData(AgentState.Error)]
    public void AgentStates_AreDefined(AgentState state)
    {
        Assert.Contains(state, Enum.GetValues<AgentState>());
    }
}
