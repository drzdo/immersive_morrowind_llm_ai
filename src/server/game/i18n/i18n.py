import math

from eventbus.data.actor_ref import ActorRef


class I18n:
    def str(self, s: str):
        return s

    def format_time(self, hour: float):
        gametime_h = math.floor(hour)
        gametime_m = math.floor((hour - gametime_h) * 60)
        gametime = f"{gametime_h} часов {gametime_m} минут"
        return gametime

    def npc_change_disposition(self, value: int):
        if value > 0:
            return f"отношение +{value}"
        else:
            return f"отношение {value}"

    def give_gold(self, me: ActorRef,
                  giver: ActorRef, giver_female: bool,
                  target: ActorRef, target_female: bool,
                  amount: int):
        given = "дала" if giver_female else "дал"

        if me == giver:
            return f"я {given} {amount} монет {target.name}"
        elif me == target:
            return f"{target.name} {given} мне {amount} монет"
        else:
            return f"{giver.name} {given} {amount} монет {target.name}"

    def give_gold_less_than_have(self, me: ActorRef,
                                 giver: ActorRef, giver_female: bool,
                                 target: ActorRef, target_female: bool,
                                 actual_amount: int, intended_amount: int):
        wanted = "хотела" if giver_female else "хотел"
        given = "дала" if giver_female else "дал"

        if me == giver:
            return f"я {wanted} дать {intended_amount} монет {target.name}, но я {given} только {actual_amount} потому что больше не было"
        elif me == target:
            return f"{target.name} {wanted} дать {intended_amount} монет мне, но {given} только {actual_amount} потому что больше не было"
        else:
            return f"{giver.name} {wanted} дать {intended_amount} монет {target.name}, но {given} только {actual_amount} потому что больше не было"

    def npc_start_follow(self, me: ActorRef, follower: ActorRef, target: ActorRef):
        if me == target:
            return f"{follower.name} следует за мной"
        else:
            return f"{follower.name} следует за {target.name}"

    def npc_stop_follow(self, me: ActorRef, follower: ActorRef, target: ActorRef):
        if me == target:
            return f"{follower.name} больше не следует за мной"
        else:
            return f"{follower.name} больше не следует за {target.name}"
