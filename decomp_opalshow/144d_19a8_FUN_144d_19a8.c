
undefined2 __cdecl16far FUN_144d_19a8(int param_1,int param_2,int param_3)

{
  uint uVar1;
  code *pcVar2;
  undefined2 uVar3;
  uint uVar4;
  undefined2 *puVar5;
  undefined2 unaff_DS;
  bool bVar6;
  undefined4 uVar7;
  
  bVar6 = false;
  if (param_3 == 0) {
    if (param_1 == 1) {
      uVar3 = FUN_144d_1a1c();
      if (!bVar6) {
        return uVar3;
      }
    }
    else {
      uVar1 = *(uint *)0x392;
      if ((param_1 != 2) && (bVar6 = uVar1 < 0x342, uVar1 != 0x342)) {
        uVar7 = FUN_144d_1a1c();
        param_2 = (int)((ulong)uVar7 >> 0x10);
        if (!bVar6) {
          return (int)uVar7;
        }
      }
      puVar5 = (undefined2 *)(uVar1 + 4);
      if ((puVar5 < (undefined2 *)0x392) && (param_2 != 0)) {
        bVar6 = (param_2 + 0xfU >> 3 & 1) != 0;
        while( true ) {
          pcVar2 = (code *)swi(0x21);
          uVar7 = (*pcVar2)();
          uVar4 = (uint)uVar7;
          if (bVar6) break;
          bVar6 = uVar4 < *(uint *)0x5ba;
          if (*(uint *)0x5ba < uVar4) {
            *puVar5 = (int)((ulong)uVar7 >> 0x10);
            *(uint *)(uVar1 + 6) = uVar4;
            *(undefined2 *)0x392 = puVar5;
            return 0;
          }
        }
      }
    }
  }
  return 0xffff;
}

