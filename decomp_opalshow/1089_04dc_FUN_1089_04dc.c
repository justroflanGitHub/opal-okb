
int __cdecl16far FUN_1089_04dc(undefined2 param_1,undefined2 param_2,undefined2 *param_3)

{
  int iVar1;
  uint uVar2;
  uint uVar3;
  undefined2 unaff_DS;
  long lVar4;
  long lVar5;
  int local_234;
  int local_232;
  int local_230;
  undefined1 local_22e [11];
  int local_223;
  char local_221;
  int local_220;
  char local_21e;
  int local_21d;
  int local_218;
  undefined2 auStack_214 [243];
  char local_2e [13];
  int local_21;
  int local_1f;
  
  iVar1 = FUN_144d_0a51(param_1,param_2,0x27,local_2e);
  if (iVar1 == 0) {
    if (local_2e[0] == '\0') {
      FUN_144d_0a9a(&local_234);
    }
    else {
      local_234 = local_2e[0] + -1;
    }
    local_230 = FUN_1089_066a(local_234,0,0,1,local_22e);
    if (local_230 == 0) {
      uVar2 = local_21e * local_218 + local_220;
      uVar3 = (local_21d * 0x20 + local_223 + -1) / local_223;
      lVar4 = FUN_144d_00c6(local_1f + -2,local_1f + -2 >> 0xf,(int)local_221,(int)local_221 >> 0xf)
      ;
      local_232 = local_223 / 0x20;
      lVar5 = FUN_144d_00fa(local_21,local_21 >> 0xf,local_232,local_232 >> 0xf);
      iVar1 = local_21 % local_232;
      local_230 = FUN_1089_066a(local_234,
                                lVar4 + CONCAT22(((int)uVar3 >> 0xf) + ((int)uVar2 >> 0xf) +
                                                 (uint)CARRY2(uVar3,uVar2),uVar3 + uVar2) + lVar5,1,
                                local_22e);
      if (local_230 == 0) {
        *param_3 = auStack_214[iVar1 * 0x10];
      }
    }
  }
  else {
    local_230 = -1;
  }
  return local_230;
}

